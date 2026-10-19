#!/usr/bin/env python3
import html, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path
from datetime import datetime
from xml.etree import ElementTree as ET

CHANNEL_ID="UCJs0ZT10hUiPRD0UZtUpI1Q"
HANDLE="@ZazoomTek"
API="https://www.googleapis.com/youtube/v3/"
KEY=os.environ.get("YOUTUBE_API_KEY", "")
TEST_PLAYLIST_ID="PL7dvpppAJr03SBwNej9rwT4nIvgYzJwzT"
GAMING_PLAYLIST_ID="PL7dvpppAJr01wOyi0xZob2R5g5NfoZGZZ"
UNBOXING_PLAYLIST_ID="PL7dvpppAJr03Tdqg6YeNWepK4sMOgIXvB"
REVIEWS_PLAYLIST_ID="PL7dvpppAJr00pUmHZxvOyTspS8Htczfr-"
ANALOGIKTEK_PLAYLIST_ID="PL7dvpppAJr02AQM7WP0D151c_JvKu_OaI"
TEST_VIDEO_IDS=set()
GAMING_VIDEO_IDS=set()
UNBOXING_VIDEO_IDS=set()
REVIEWS_VIDEO_IDS=set()
ANALOGIKTEK_VIDEO_IDS=set()
# Only creator-confirmed complete, original sessions belong in GAMEPLAY.
# These exact IDs can be curated without guessing from titles.
GAMEPLAY_ORIGINAL_IDS=set()
GAMEPLAY_EDITORIAL_IDS=set()
GAMEPLAY_CONFIG=Path(__file__).resolve().parent.parent/"gameplay-video-rules.json"

def load_gameplay_rules():
    rules=json.loads(GAMEPLAY_CONFIG.read_text(encoding="utf-8"))
    if not isinstance(rules,dict):
        raise RuntimeError("Gameplay rules must be a JSON object")
    keys=("original_gameplay_ids","edited_gaming_ids")
    for key in keys:
        if not isinstance(rules.get(key),list) or not all(
            isinstance(x,str) and re.fullmatch(r"[A-Za-z0-9_-]{11}",x)
            for x in rules[key]
        ):
            raise RuntimeError("Invalid Gameplay video rule list: "+key)
    original=set(rules["original_gameplay_ids"])
    editorial=set(rules["edited_gaming_ids"])
    if original & editorial:
        raise RuntimeError("Video cannot be both original GAMEPLAY and edited GAMING")
    return original,editorial

def get(endpoint, **params):
    """YouTube API request with retries for temporary network/server errors."""
    params["key"]=KEY
    url=API+endpoint+"?"+urllib.parse.urlencode(params)
    last_error=None
    for attempt in range(4):
        try:
            req=urllib.request.Request(
                url,
                headers={"User-Agent":"ZazoomTek-Sync/1.0","Accept":"application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as err:
            last_error=err
            # Authentication/configuration errors should fail immediately.
            if err.code not in (429,500,502,503,504):
                raise
        except (urllib.error.URLError, ConnectionResetError, TimeoutError) as err:
            last_error=err

        if attempt<3:
            wait=2 ** (attempt+1)
            print(f"YouTube request failed temporarily ({last_error}); retrying in {wait}s...")
            time.sleep(wait)

    raise last_error

def official_rss_recent_ids(previous_ids, playlist_ids):
    """Cross-check the official channel Atom feed if the uploads playlist is stale.

    IDs are later verified through videos.list to belong to this exact channel.
    An unreachable RSS endpoint never prevents ordinary Data API imports.
    """
    endpoint="https://www.youtube.com/feeds/videos.xml?channel_id="+CHANNEL_ID
    try:
        req=urllib.request.Request(endpoint,headers={
            "User-Agent":"Mozilla/5.0","Accept":"application/atom+xml","Cache-Control":"no-cache"})
        with urllib.request.urlopen(req,timeout=10) as response:
            payload=response.read(350000)
        root=ET.fromstring(payload)
        namespace={"atom":"http://www.w3.org/2005/Atom",
                   "yt":"http://www.youtube.com/xml/schemas/2015"}
        channel=root.findtext("yt:channelId",default="",namespaces=namespace)
        # Atom feeds expose the channel ID without YouTube's "UC" prefix.
        # The videos.list verification below still checks the full channel ID.
        if channel not in (CHANNEL_ID,CHANNEL_ID[2:]):
            raise RuntimeError("Channel ID mismatch on official RSS")
        ids=[]
        for entry in root.findall("atom:entry",namespace):
            pid=(entry.findtext("yt:videoId",default="",namespaces=namespace) or "").strip()
            if re.fullmatch(r"[A-Za-z0-9_-]{11}",pid) and pid not in ids:
                ids.append(pid)
        missing=[pid for pid in ids if pid not in previous_ids and pid not in playlist_ids]
        if missing:
            print(f"Official YouTube Atom feed lists {len(missing)} new upload(s) missing from the first playlist scan.")
        return missing
    except Exception as err:
        print(f"Official Atom feed temporarily unavailable; verified API scan continues: {err}")
        return []


def safe_playlist_ids(playlist_id, category, previous):
    """One broken/empty editorial playlist must never block new channel uploads."""
    backup={v["id"] for v in previous if isinstance(v,dict)
            and v.get("id") and (v.get("category")==category
            or (category=="gaming" and v.get("category")=="gameplay"))}
    try:
        found=playlist_video_ids(playlist_id)
        if not found and backup:
            print(f"Playlist {category} was unexpectedly empty; preserving {len(backup)} known associations.")
            return backup
        return found
    except Exception as err:
        print(f"Playlist {category} temporarily unavailable; retaining {len(backup)} associations: {err}")
        return backup


def cached_video(item):
    """Rebuild the small API-like shape needed by the renderer from saved state."""
    live=bool(item.get("live"))
    return {
        "id":item.get("id"),
        "snippet":{
            "title":item.get("title") or "",
            "publishedAt":item.get("publishedAt") or "1970-01-01T00:00:00Z",
            "liveBroadcastContent":"live" if live else "none",
        },
        "contentDetails":{"duration":"PT0S"},
        "_cached_short":bool(item.get("short")),
        "_cached_live":live,
        "_cached_completed_live":bool(item.get("completedLive")),
        "_cached_original_gameplay":bool(item.get("gameplayOriginal")),
    }

def uploads(previous=None, recent_limit=100):
    """Fetch only recent uploads, then merge them with the last valid full state.

    This keeps the five-minute sync well below unnecessary YouTube API load while
    retaining the complete historic catalogue needed by category pages.
    """
    previous=previous or []
    c=get("channels",part="contentDetails",id=CHANNEL_ID)
    items=c.get("items") or []
    if not items:
        raise RuntimeError("YouTube channels response contained no channel.")
    pl=items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    # On first bootstrap there is no cache, so build the complete history.
    limit=None if not previous else recent_limit
    ids=[]
    token=None
    while True:
        params={"part":"snippet,contentDetails","playlistId":pl,"maxResults":50}
        if token: params["pageToken"]=token
        p=get("playlistItems",**params)
        batch=[
            x.get("contentDetails",{}).get("videoId")
            for x in p.get("items",[])
            if x.get("contentDetails",{}).get("videoId")
        ]
        ids.extend(batch)
        token=p.get("nextPageToken")
        if limit and len(ids)>=limit:
            ids=ids[:limit]
            break
        if not token:
            break

    if previous and not ids:
        raise RuntimeError("YouTube recent uploads response was empty.")

    # A second official channel source reduces the chance of a late-upload gap.
    previous_ids={v.get("id") for v in previous if isinstance(v,dict) and v.get("id")}
    missing=official_rss_recent_ids(previous_ids,set(ids))
    if missing:
        ids=list(dict.fromkeys(missing+ids))

    fresh=[]
    for i in range(0,len(ids),50):
        fresh.extend(
            get(
                "videos",
                part="snippet,contentDetails,liveStreamingDetails",
                id=",".join(ids[i:i+50])
            ).get("items",[])
        )
    # Only import videos that YouTube confirms were published by this channel.
    fresh=[v for v in fresh if v.get("snippet",{}).get("channelId",CHANNEL_ID)==CHANNEL_ID]
    fresh=sorted(fresh,key=lambda x:x["snippet"]["publishedAt"],reverse=True)

    if not previous:
        return fresh

    fresh_ids={v["id"] for v in fresh}
    cutoff=min((v["snippet"]["publishedAt"] for v in fresh),default="")
    merged=list(fresh)

    # Preserve older cached history, but do not resurrect a recent video that
    # disappeared from the channel's upload feed.
    for item in previous:
        if not isinstance(item,dict) or not item.get("id") or item["id"] in fresh_ids:
            continue
        published=item.get("publishedAt") or ""
        if cutoff and published>=cutoff:
            continue
        merged.append(cached_video(item))

    return sorted(merged,key=lambda x:x["snippet"]["publishedAt"],reverse=True)

def sec(d):
    m=re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?",d or "")
    return (int(m.group(1) or 0)*3600+int(m.group(2) or 0)*60+int(m.group(3) or 0)) if m else 0

def is_live_upload(v):
    # Exclude broadcasts that are currently live or still upcoming.
    live_state=(v.get("snippet",{}).get("liveBroadcastContent") or "none").lower()
    return live_state in ("live","upcoming")

def is_completed_broadcast(v):
    # YouTube keeps liveStreamingDetails on completed Live/Premiere videos.
    # A completed broadcast is treated as a normal editorial video only after
    # the user explicitly assigns it to one of the site's YouTube playlists.
    live_state=(v.get("snippet",{}).get("liveBroadcastContent") or "none").lower()
    return live_state=="none" and (bool(v.get("_cached_completed_live")) or bool(v.get("liveStreamingDetails",{}).get("actualEndTime")))

def youtube_short_ids():
    # YouTube Data API doesn't expose a direct isShort flag.
    # Read the channel Shorts shelf. Return None on a temporary fetch failure so
    # main() can preserve the last known-good Short IDs instead of emptying UI.
    try:
        req=urllib.request.Request(
            f"https://www.youtube.com/{HANDLE}/shorts",
            headers={"User-Agent":"Mozilla/5.0"}
        )
        last_error=None
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req,timeout=30) as r:
                    page=r.read().decode("utf-8","ignore")
                ids=set(re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"',page))
                ids.update(re.findall(r'/shorts/([A-Za-z0-9_-]{11})',page))
                return ids
            except (urllib.error.URLError,ConnectionResetError,TimeoutError) as err:
                last_error=err
                if attempt<3:
                    time.sleep(2 ** (attempt+1))
        print(f"Shorts shelf temporarily unavailable: {last_error}")
        return None
    except Exception as err:
        print(f"Shorts shelf temporarily unavailable: {err}")
        return None

def playlist_video_ids(playlist_id):
    ids=set()
    token=None
    while True:
        params={"part":"contentDetails","playlistId":playlist_id,"maxResults":50}
        if token: params["pageToken"]=token
        p=get("playlistItems",**params)
        ids.update(x["contentDetails"]["videoId"] for x in p.get("items",[]) if x.get("contentDetails",{}).get("videoId"))
        token=p.get("nextPageToken")
        if not token: break
    return ids

def has_gameplay_in_title(v):
    title=v.get("snippet",{}).get("title") or ""
    return re.search(r"\b(?:gameplay|gamepaly)\b",title,re.IGNORECASE) is not None

def original_gameplay_description_marker(v):
    """A marker deliberately placed by the channel owner, not a guess."""
    return bool(v.get("_cached_original_gameplay")) or (
        "#ZTGameplayOriginale" in (v.get("snippet",{}).get("description") or "")
    )

def is_original_gameplay(v):
    """GAMEPLAY only for creator-marked original, continuous gameplay sessions.

    Do not infer authorship, completeness or lack of editing from the word
    'gameplay' alone. Editorial, trailer and montage uploads remain GAMING.
    """
    vid=v.get("id")
    title=v.get("snippet",{}).get("title") or ""
    if vid in GAMEPLAY_EDITORIAL_IDS:
        return False
    if vid in GAMEPLAY_ORIGINAL_IDS:
        return True  # Explicitly verified by site editor.
    if not has_gameplay_in_title(v):
        return False
    # Exclude clear signs of third-party footage or editorial montages.
    if re.search(r"\b(trailer|teaser|reveal|anteprima|recensione|reaction|"
                 r"commento|commenti|commentato|montaggio|montato|spezzoni|"
                 r"spezzettato|analisi|highlights?|news)\b",title,re.I):
        return False
    if original_gameplay_description_marker(v):
        return True
    # Explicit self-descriptions of an uninterrupted session, not just "Gameplay".
    return re.search(
        r"\b(?:lungo|full|long|uncut)\s+(?:gameplay|gamepaly)\b|"
        r"\b(?:gameplay|gamepaly)\s+(?:completo|integrale|senza\s+tagli)\b",
        title,re.I
    ) is not None

def classify(v):
    # Reviews/tests/unboxings keep their editorial playlist categories.
    if v["id"] in REVIEWS_VIDEO_IDS: return "recensioni"
    if v["id"] in UNBOXING_VIDEO_IDS: return "unboxing"
    if v["id"] in TEST_VIDEO_IDS: return "test"
    if v["id"] in ANALOGIKTEK_VIDEO_IDS: return "analogiktek"
    # Self-recorded complete sessions are distinct from gameplay news/montages.
    if is_original_gameplay(v): return "gameplay"
    if v["id"] in GAMING_VIDEO_IDS or has_gameplay_in_title(v):
        return "gaming"
    return None

def esc(s): return html.escape(s,quote=True)

def card(v):
    s=v["snippet"]; vid=v["id"]; title=esc(s["title"])
    dt=datetime.fromisoformat(s["publishedAt"].replace("Z","+00:00"))
    months=["GEN","FEB","MAR","APR","MAG","GIU","LUG","AGO","SET","OTT","NOV","DIC"]
    date=f"{dt.day:02d} {months[dt.month-1]} {dt.year}"
    return f'''    <article class="video-card">
      <button type="button" data-video="{vid}" onclick="playVideo(this)" aria-label="Riproduci {title}">
        <img src="https://i.ytimg.com/vi/{vid}/maxresdefault.jpg" onerror="this.onerror=null;this.src='https://i.ytimg.com/vi/{vid}/hqdefault.jpg'" alt="{title}" loading="lazy" decoding="async">
      </button>
      <div class="video-card-body"><span class="video-date">{date}</span><h3>{title}</h3><a href="https://youtu.be/{vid}" target="_blank" rel="noopener">Guarda su YouTube</a></div>
    </article>'''

def update_category(category_name, vids, short_ids):
    p=Path(category_name+".html")
    if not p.exists():
        return

    h=p.read_text(encoding="utf-8")

    # Category pages: show the 20 newest videos belonging to that exact
    # YouTube playlist/category, strictly newest -> oldest.
    candidates=[v for v in vids if classify(v)==category_name]
    candidates.sort(key=lambda v:v["snippet"]["publishedAt"], reverse=True)
    chosen=candidates[:20]

    a=h.find('<section class="video-grid">')
    if a<0:
        return
    b=h.find("</section>",a)
    if b<0:
        return

    block='<section class="video-grid">\n'+"\n".join(card(v) for v in chosen)+'\n  </section>'
    p.write_text(h[:a]+block+h[b+10:],encoding="utf-8")

def replace_article_containing(text, needle, new_article):
    pos=text.find(needle)
    if pos<0: return text
    start=text.rfind("<article",0,pos)
    end=text.find("</article>",pos)
    if start<0 or end<0: return text
    return text[:start]+new_article+text[end+10:]

def feature_main(v):
    vid=v["id"]; title=esc(v["snippet"]["title"])
    return f'''<article class="feature-main">
      <div class="media">
        <button type="button" data-video="{vid}" onclick="playVideo(this)">
          <img src="https://i.ytimg.com/vi/{vid}/hqdefault.jpg" alt="{title}">
        </button>
      </div>
      <div class="feature-copy">
        <a class="tag" href="https://www.youtube.com/watch?v={vid}" target="_blank" rel="noopener" aria-label="Apri l'ultimo video">Ultimo video</a>
        <h3>{title}</h3>
      </div>
    </article>'''

def feature_side(v, name):
    vid=v["id"]; title=esc(v["snippet"]["title"])
    label={"recensioni":"Recensioni","test":"Test","unboxing":"Unboxing","gaming":"Gaming"}[name]
    aria={"recensioni":"recensioni","test":"test","unboxing":"unboxing","gaming":"video Gaming"}[name]
    return f'''<article class="feature-card">
        <div class="media">
          <button type="button" data-video="{vid}" onclick="playVideo(this)">
            <img src="https://i.ytimg.com/vi/{vid}/hqdefault.jpg" alt="{title}">
          </button>
        </div>
        <div class="feature-copy">
          <a class="tag" href="{name}.html" aria-label="Apri tutti i {aria}">{label}</a>
          <h3>{title}</h3>
        </div>
      </article>'''

def recent_short(v):
    vid=v["id"]; title=esc(v["snippet"]["title"])
    dt=datetime.fromisoformat(v["snippet"]["publishedAt"].replace("Z","+00:00"))
    months=["Gen","Feb","Mar","Apr","Mag","Giu","Lug","Ago","Set","Ott","Nov","Dic"]
    date=f"{dt.day:02d} {months[dt.month-1]} {dt.year}"
    return f'''    <article class="recent-card">
      <div class="media">
        <button type="button" data-video="{vid}" onclick="playVideo(this)">
          <img src="https://i.ytimg.com/vi/{vid}/hqdefault.jpg" alt="{title}">
        </button>
      </div>
      <div class="recent-copy">
        <h3>{title}</h3>
        <p>Shorts · {date}</p>
      </div>
    </article>'''

def analogic_card(v):
    vid=v["id"]; title=esc(v["snippet"]["title"])
    return f'''      <article class="analogic-card">
        <a href="https://www.youtube.com/watch?v={vid}&list={ANALOGIKTEK_PLAYLIST_ID}" target="_blank" rel="noopener">
          <img src="https://i.ytimg.com/vi/{vid}/maxresdefault.jpg" onerror="this.src='https://i.ytimg.com/vi/{vid}/hqdefault.jpg'" alt="{title}" loading="lazy">
          <h3>{title}</h3>
        </a>
      </article>'''


def home_video_card(v):
    vid=v["id"]; title=esc(v["snippet"]["title"])
    return f'''          <article class="video-card"><button class="video-thumb" data-video="{vid}" onclick="playVideo(this)"><img src="https://i.ytimg.com/vi/{vid}/maxresdefault.jpg" onerror="this.onerror=null;this.src='https://i.ytimg.com/vi/{vid}/hqdefault.jpg'" alt="{title}" loading="lazy"></button><h3>{title}</h3></article>'''

def side_video_card(v, label):
    vid=v["id"]; title=esc(v["snippet"]["title"])
    dt=datetime.fromisoformat(v["snippet"]["publishedAt"].replace("Z","+00:00"))
    months=["gennaio","febbraio","marzo","aprile","maggio","giugno","luglio","agosto","settembre","ottobre","novembre","dicembre"]
    date=f"{dt.day} {months[dt.month-1]} {dt.year}"
    return f'''        <article class="side-video"><button class="video-thumb" data-video="{vid}" onclick="playVideo(this)"><img src="https://i.ytimg.com/vi/{vid}/maxresdefault.jpg" onerror="this.onerror=null;this.src='https://i.ytimg.com/vi/{vid}/hqdefault.jpg'" alt="{title}" loading="lazy"></button><div><h3>{title}</h3><small>{date}</small></div></article>'''


def sidebar_latest_video_card(v):
    vid=v["id"]; title=esc(v["snippet"]["title"])
    dt=datetime.fromisoformat(v["snippet"]["publishedAt"].replace("Z","+00:00"))
    months=["gennaio","febbraio","marzo","aprile","maggio","giugno","luglio","agosto","settembre","ottobre","novembre","dicembre"]
    date=f"{dt.day} {months[dt.month-1]} {dt.year}"
    return (
        f'          <article class="zt-sidebar-card">'
        f'<button class="video-thumb" data-video="{vid}" onclick="playVideo(this)">'
        f'<img src="https://i.ytimg.com/vi/{vid}/maxresdefault.jpg" '
        f'onerror="this.onerror=null;this.src=\'https://i.ytimg.com/vi/{vid}/hqdefault.jpg\'" '
        f'alt="{title}" loading="lazy"></button>'
        f'<div class="zt-sidebar-copy"><h3>{title}</h3><small>{date}</small></div></article>'
    )


def sidebar_stack_card(v, category_override=None):
    vid=v["id"]; title=esc(v["snippet"]["title"])
    category=category_override or classify(v)
    category_label={
        "recensioni":"RECENSIONI",
        "test":"TEST",
        "unboxing":"UNBOXING",
        "gaming":"GAMING",
        "gameplay":"GAMEPLAY",
        "analogiktek":"ANALOGICTEK",
    }.get(category,(category or "VIDEO").upper())
    dt=datetime.fromisoformat(v["snippet"]["publishedAt"].replace("Z","+00:00"))
    months=["gennaio","febbraio","marzo","aprile","maggio","giugno","luglio","agosto","settembre","ottobre","novembre","dicembre"]
    date=f"{dt.day} {months[dt.month-1]} {dt.year}"
    return (
        f'          <article class="zt-stack-card" data-category="{esc(category or "")}">'
        f'<button class="video-thumb" data-video="{vid}" onclick="playVideo(this)">'
        f'<img src="https://i.ytimg.com/vi/{vid}/maxresdefault.jpg" '
        f'onerror="this.onerror=null;this.src=\'https://i.ytimg.com/vi/{vid}/hqdefault.jpg\'" '
        f'alt="{title}" loading="lazy"></button>'
        f'<div class="zt-stack-copy">'
        f'<h3>{title}</h3><span class="zt-stack-category">{category_label}</span>'
        f'<small>{date}</small></div></article>'
    )

def sidebar_short_card(v):
    vid=v["id"]; title=esc(v["snippet"]["title"])
    return f'''          <article class="side-video zt-short-card"><button class="video-thumb" data-video="{vid}" onclick="playVideo(this)"><img src="https://i.ytimg.com/vi/{vid}/maxresdefault.jpg" onerror="this.onerror=null;this.src='https://i.ytimg.com/vi/{vid}/hqdefault.jpg'" alt="{title}" loading="lazy"></button><div><h3>{title}</h3><small>Shorts</small></div></article>'''


def sidebar_short_slide_card(v):
    vid=v["id"]; title=esc(v["snippet"]["title"])
    dt=datetime.fromisoformat(v["snippet"]["publishedAt"].replace("Z","+00:00"))
    months=["gennaio","febbraio","marzo","aprile","maggio","giugno","luglio","agosto","settembre","ottobre","novembre","dicembre"]
    date=f"{dt.day} {months[dt.month-1]} {dt.year}"
    return (
        f'          <article class="zt-short-slide">'
        f'<div class="zt-short-media"><button class="video-thumb" data-video="{vid}" onclick="playVideo(this)">'
        f'<img src="https://i.ytimg.com/vi/{vid}/maxresdefault.jpg" '
        f'onerror="this.onerror=null;this.src=\'https://i.ytimg.com/vi/{vid}/hqdefault.jpg\'" '
        f'alt="{title}" loading="lazy"></button></div>'
        f'<div class="zt-short-copy"><h3>{title}</h3><small>{date}</small></div></article>'
    )

def sidebar_analog_card(v):
    vid=v["id"]; title=esc(v["snippet"]["title"])
    dt=datetime.fromisoformat(v["snippet"]["publishedAt"].replace("Z","+00:00"))
    months=["gennaio","febbraio","marzo","aprile","maggio","giugno","luglio","agosto","settembre","ottobre","novembre","dicembre"]
    date=f"{dt.day} {months[dt.month-1]} {dt.year}"
    return f'''          <article class="side-video"><button class="video-thumb" data-video="{vid}" onclick="playVideo(this)"><img src="https://i.ytimg.com/vi/{vid}/maxresdefault.jpg" onerror="this.onerror=null;this.src='https://i.ytimg.com/vi/{vid}/hqdefault.jpg'" alt="{title}" loading="lazy"></button><div><h3>{title}</h3><small>{date}</small></div></article>'''

def replace_marker_block(text, start_marker, end_marker, inner):
    pat=re.escape(start_marker)+r'.*?'+re.escape(end_marker)
    repl=start_marker+"\n"+inner+"\n        "+end_marker
    return re.sub(pat,repl,text,flags=re.S)

def update_home(vids, short_ids):
    p=Path("index.html")
    h=p.read_text(encoding="utf-8")

    # Main featured: newest long-form video only. Shorts never enter the large box.
    # Prefer the channel Shorts shelf; use duration as a fallback when that shelf
    # cannot be read. This change is intentionally isolated to the main feature.
    # Main feature: newest true 16:9 long-form upload, regardless of category.
    # Shorts/vertical videos never enter the large box.
    ratio_cache={}

    def video_aspect_ratio(v):
        """Return the real source width/height ratio from YouTube player data."""
        vid=v["id"]
        if vid in ratio_cache:
            return ratio_cache[vid]
        ratio=None
        try:
            req=urllib.request.Request(
                f"https://www.youtube.com/watch?v={vid}",
                headers={"User-Agent":"Mozilla/5.0","Accept-Language":"it-IT,it;q=0.9,en;q=0.8"}
            )
            with urllib.request.urlopen(req,timeout=12) as r:
                page=r.read().decode("utf-8","ignore")
            marker="ytInitialPlayerResponse"
            pos=page.find(marker)
            if pos>=0:
                brace=page.find("{",pos)
                if brace>=0:
                    depth=0; in_str=False; escp=False; endpos=None
                    for i,ch in enumerate(page[brace:],start=brace):
                        if in_str:
                            if escp: escp=False
                            elif ch=="\\": escp=True
                            elif ch=='"': in_str=False
                        else:
                            if ch=='"': in_str=True
                            elif ch=="{": depth+=1
                            elif ch=="}":
                                depth-=1
                                if depth==0:
                                    endpos=i+1
                                    break
                    if endpos:
                        data=json.loads(page[brace:endpos])
                        fmts=(data.get("streamingData",{}).get("adaptiveFormats",[]) or
                              data.get("streamingData",{}).get("formats",[]))
                        dims=[(x.get("width"),x.get("height")) for x in fmts if x.get("width") and x.get("height")]
                        if dims:
                            w,h=max(dims,key=lambda x:x[0]*x[1])
                            ratio=float(w)/float(h)
        except Exception:
            ratio=None
        ratio_cache[vid]=ratio
        return ratio

    def is_true_landscape(v):
        # Never allow known Shorts or active/upcoming live streams.
        if v["id"] in short_ids or is_live_upload(v):
            return False
        # Completed Live/Premiere videos require an explicit editorial playlist.
        # Example: they become Gaming only after being added to the Gaming playlist.
        if is_completed_broadcast(v) and classify(v) is None:
            return False
        ratio=video_aspect_ratio(v)
        # YouTube does not always expose source dimensions to the workflow.
        # In that case the Shorts shelf remains the authoritative separator:
        # a normal, non-live upload must stay visible instead of blanking Home.
        if ratio is None:
            return True
        return 1.70 <= ratio <= 1.82

    def is_true_vertical_short(v):
        if is_live_upload(v) or v["id"] not in short_ids:
            return False
        ratio=video_aspect_ratio(v)
        # If dimensions are temporarily unavailable, keep a video that YouTube
        # itself placed on the Shorts shelf. When dimensions are available,
        # require a true portrait 9:16-ish source.
        if ratio is None:
            return True
        return 0.54 <= ratio <= 0.59

    # Choose the newest upload by YouTube publish date, but never a known Short.
    # For ZazoomTek the upload order is authoritative; vertical Shorts are removed
    # by the Shorts shelf before selecting the main Home feature.
    ordered=sorted(vids,key=lambda v:v["snippet"]["publishedAt"],reverse=True)
    main_video=next((v for v in ordered if is_true_landscape(v)),None)
    if main_video:
        a=h.find('<article class="feature-main">')
        if a>=0:
            b=h.find("</article>",a)
            if b>=0: h=h[:a]+feature_main(main_video)+h[b+10:]

    # IMPORTANT: obsolete feature-side updater disabled.
    # The current Home uses the real right sidebar links (recensioni.html,
    # test.html, unboxing.html, gaming.html). A global href search here can
    # mistake those links for old feature cards and delete the Home structure.
    # Sidebar videos are updated safely later through explicit marker blocks.

    # Lower category thumbnails: same rule, newest upload by YouTube publish date.
    for name in ["recensioni","test","unboxing","gaming"]:
        candidates=[v for v in vids if classify(v)==name]
        candidates.sort(key=lambda v:v["snippet"]["publishedAt"], reverse=True)
        latest=candidates[0] if candidates else None
        if not latest: continue
        marker=f'<article class="category-box category-latest" data-page="{name}.html">'
        pos=h.find(marker)
        if pos<0: continue
        end=h.find("</article>",pos)
        segment=h[pos:end+10]
        vid=latest["id"]
        segment=re.sub(
            r'<img src="https://i\.ytimg\.com/vi/[^/]+/maxresdefault\.jpg" onerror="this\.src=\'https://i\.ytimg\.com/vi/[^/]+/hqdefault\.jpg\'"',
            f'<img src="https://i.ytimg.com/vi/{vid}/maxresdefault.jpg" onerror="this.src=\'https://i.ytimg.com/vi/{vid}/hqdefault.jpg\'"',
            segment,count=1
        )
        h=h[:pos]+segment+h[end+10:]

    # Exactly five latest REAL 9:16 Shorts, newest -> oldest.
    # Do not use duration alone: only videos that are on the Shorts shelf AND
    # whose source dimensions are truly vertical are allowed here.
    shorts=[]
    for v in ordered:
        if is_true_vertical_short(v):
            shorts.append(v)
            if len(shorts)>=5:
                break

    # Home sidebar Shorts carousel: always the five newest real Shorts.
    h=replace_marker_block(
        h,"<!-- SIDEBAR_SHORTS_CAROUSEL_START -->","<!-- SIDEBAR_SHORTS_CAROUSEL_END -->",
        "\n".join(sidebar_short_slide_card(v) for v in shorts)
    )
    a=h.find('<section class="recent-grid" id="shorts-grid">')
    if a>=0:
        b=h.find("</section>",a)
        if b>=0:
            block='<section class="recent-grid" id="shorts-grid">\n'+"\n".join(recent_short(v) for v in shorts)+'\n  </section>'
            h=h[:a]+block+h[b+10:]

    # AnalogikTek: five newest videos from the official playlist.
    analog=[v for v in vids if v["id"] in ANALOGIKTEK_VIDEO_IDS][:5]
    a=h.find('<div class="analogic-grid">')
    if a>=0:
        b=h.find("</div>",a)
        if b>=0:
            block='<div class="analogic-grid">\n'+"\n".join(analogic_card(v) for v in analog)+'\n    </div>'
            h=h[:a]+block+h[b+6:]

    # "Ultimi Video": latest 16:9 video per actual editorial category.
    # Only confirmed original full sessions qualify for GAMEPLAY; any edited,
    # commented or trailer material with "Gameplay" belongs in GAMING.
    # "Esplora video" uses these same authoritative category labels.
    selected={}
    for category in ("recensioni","test","unboxing","gaming","analogiktek"):
        selected[category]=next((
            v for v in ordered
            if classify(v)==category
            and not is_completed_broadcast(v)
            and is_true_landscape(v)
        ),None)

    # GAMEPLAY requires creator confirmation / explicit full-session marker.
    # Exclude Shorts and prevent duplicates with the other category cards.
    used={v["id"] for v in selected.values() if v}
    gameplay=next((
        v for v in ordered
        if classify(v)=="gameplay"
        and not is_live_upload(v)
        and v["id"] not in short_ids
        and not bool(v.get("_cached_short"))
        and v["id"] not in used
        and is_true_landscape(v)
    ),None)
    if gameplay:
        selected["gameplay"]=gameplay

    stack=sorted(
        (v for v in selected.values() if v),
        key=lambda v:v["snippet"]["publishedAt"],
        reverse=True
    )
    gameplay_id=gameplay["id"] if gameplay else None
    h=replace_marker_block(
        h,"<!-- SIDEBAR_STACK_VIDEOS_START -->","<!-- SIDEBAR_STACK_VIDEOS_END -->",
        "\n".join(sidebar_stack_card(v,"gameplay" if v["id"]==gameplay_id else None) for v in stack)
    )
    editorial_latest=stack[:5]
    # Right sidebar: exactly the five newest regular landscape uploads,
    # ordered newest -> oldest. The visual carousel itself lives in index.html.
    h=replace_marker_block(
        h,"<!-- SIDEBAR_LATEST_VIDEOS_START -->","<!-- SIDEBAR_LATEST_VIDEOS_END -->",
        "\n".join(sidebar_latest_video_card(v) for v in editorial_latest)
    )
    # Resolve the newest Short before choosing the right-sidebar category cards.
    # This lets us explicitly exclude it from every category box.
    sidebar_short=next((v for v in shorts),None)
    sidebar_short_id=sidebar_short["id"] if sidebar_short else None

    editorial_markers={
        "recensioni":("<!-- VIDEO_REVIEWS_START -->","<!-- VIDEO_REVIEWS_END -->","Recensioni"),
        "test":("<!-- VIDEO_TEST_START -->","<!-- VIDEO_TEST_END -->","Test"),
        "unboxing":("<!-- VIDEO_UNBOXING_START -->","<!-- VIDEO_UNBOXING_END -->","Unboxing"),
        "gaming":("<!-- VIDEO_GAMING_START -->","<!-- VIDEO_GAMING_END -->","Gaming"),
    }

    for category,(start_marker,end_marker,label) in editorial_markers.items():
        # ALL right-sidebar category boxes: ONLY true 16:9 videos.
        # Never show Shorts / 9:16, never show live streams.
        # Keep chronological order and take the newest valid landscape video.
        candidate=next(
            (
                v for v in ordered
                if classify(v)==category
                and v["id"] not in short_ids
                and not is_live_upload(v)
                and not is_completed_broadcast(v)
                and is_true_landscape(v)
            ),
            None
        )
        h=replace_marker_block(
            h,start_marker,end_marker,
            side_video_card(candidate,label) if candidate else ""
        )

    # Sidebar: newest real Short.
    h=replace_marker_block(
        h,"<!-- SIDEBAR_SHORT_START -->","<!-- SIDEBAR_SHORT_END -->",
        sidebar_short_card(sidebar_short) if sidebar_short else ""
    )

    # Sidebar: newest video from the official AnalogikTek playlist.
    sidebar_analog=next((v for v in ordered if v["id"] in ANALOGIKTEK_VIDEO_IDS and not is_live_upload(v)),None)
    h=replace_marker_block(
        h,"<!-- SIDEBAR_ANALOG_START -->","<!-- SIDEBAR_ANALOG_END -->",
        sidebar_analog_card(sidebar_analog) if sidebar_analog else ""
    )

    # Cache-busting build marker.
    h=re.sub(r'<meta name="zazoomtek-build" content="[^"]*">',
             f'<meta name="zazoomtek-build" content="{vids[0]["id"]}-{vids[0]["snippet"]["publishedAt"]}">',h,count=1)
    p.write_text(h,encoding="utf-8")

def main():
    global TEST_VIDEO_IDS, GAMING_VIDEO_IDS, UNBOXING_VIDEO_IDS, REVIEWS_VIDEO_IDS, ANALOGIKTEK_VIDEO_IDS
    global GAMEPLAY_ORIGINAL_IDS, GAMEPLAY_EDITORIAL_IDS

    state_path=Path(".youtube-latest.json")
    previous=[]
    if state_path.exists():
        try:
            previous=json.loads(state_path.read_text(encoding="utf-8"))
            if not isinstance(previous,list):
                previous=[]
        except Exception:
            previous=[]

    replay = "--render-from-cache" in sys.argv
    cache_file = Path(".youtube-master-render-cache.json")
    if replay:
        cache=json.loads(cache_file.read_text(encoding="utf-8"))
        vids=cache.get("videos", [])
        if (not isinstance(vids, list) or len(vids)<20 or
                any(not isinstance(v, dict) or not isinstance(v.get("id"), str)
                    or "snippet" not in v for v in vids)):
            raise RuntimeError("Missing or corrupted YouTube full-video render cache")
        if len({v["id"] for v in vids}) != len(vids):
            raise RuntimeError("Duplicated video IDs in JSON render cache")
        GAMEPLAY_ORIGINAL_IDS,GAMEPLAY_EDITORIAL_IDS=load_gameplay_rules()
        sets=cache.get("playlists", {})
        for key in ("test","gaming","unboxing","recensioni","analogiktek"):
            if not isinstance(sets.get(key), list):
                raise RuntimeError("Missing playlist cache: "+key)
        TEST_VIDEO_IDS=set(sets["test"])
        GAMING_VIDEO_IDS=set(sets["gaming"])
        UNBOXING_VIDEO_IDS=set(sets["unboxing"])
        REVIEWS_VIDEO_IDS=set(sets["recensioni"])
        ANALOGIKTEK_VIDEO_IDS=set(sets["analogiktek"])
        short_ids=set(cache.get("short_ids", []))
        if any(not isinstance(x,str) for x in short_ids):
            raise RuntimeError("Malformed Short ID cache")
        os.environ["ZT_FORCE_SYNC"]="true"
        print("MASTER VIDEO ADAPTER: rendering validated JSON cache without new API import")
    else:
        vids=uploads(previous)
        if not vids:
            raise RuntimeError("YouTube safety check failed: zero uploads returned.")
    
        # Protect the site from a transient partial API response.
        if previous:
            minimum=max(20,int(len(previous)*0.80))
            if len(vids)<minimum:
                raise RuntimeError(
                    f"YouTube safety check failed: received {len(vids)} videos, "
                    f"previous valid state had {len(previous)}. Site left unchanged."
                )
    
        GAMEPLAY_ORIGINAL_IDS,GAMEPLAY_EDITORIAL_IDS=load_gameplay_rules()
        TEST_VIDEO_IDS=safe_playlist_ids(TEST_PLAYLIST_ID,"test",previous)
        GAMING_VIDEO_IDS=safe_playlist_ids(GAMING_PLAYLIST_ID,"gaming",previous)
        UNBOXING_VIDEO_IDS=safe_playlist_ids(UNBOXING_PLAYLIST_ID,"unboxing",previous)
        REVIEWS_VIDEO_IDS=safe_playlist_ids(REVIEWS_PLAYLIST_ID,"recensioni",previous)
        ANALOGIKTEK_VIDEO_IDS=safe_playlist_ids(ANALOGIKTEK_PLAYLIST_ID,"analogiktek",previous)
    
        # Previously approved playlist classifications are preserved by safe_playlist_ids.
        # The main uploader still sees all public channel videos when a playlist fails.
    
        short_ids=youtube_short_ids()
        if short_ids is None:
            short_ids={
                item.get("id") for item in previous
                if isinstance(item,dict) and item.get("short") and item.get("id")
            }
            print(f"Using {len(short_ids)} last known-good Short IDs from state.")
    
        cache_payload={
            "videos": vids,
            "playlists": {
                "test": sorted(TEST_VIDEO_IDS), "gaming": sorted(GAMING_VIDEO_IDS),
                "unboxing": sorted(UNBOXING_VIDEO_IDS), "recensioni": sorted(REVIEWS_VIDEO_IDS),
                "analogiktek": sorted(ANALOGIKTEK_VIDEO_IDS)},
            "short_ids": sorted(short_ids),
        }
        cache_file.write_text(json.dumps(cache_payload,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    # Use the verified API/playlist state to determine whether any video,
    # category, Short, or completed livestream actually changed. Rebuilding
    # all category pages on an unchanged poll needlessly consumes Hosting quota.
    new_state=[{
        "id":v["id"],
        "title":v["snippet"]["title"],
        "publishedAt":v["snippet"]["publishedAt"],
        "category":classify(v),
        "gameplayOriginal":original_gameplay_description_marker(v),
        "short": (v["id"] in short_ids) or bool(v.get("_cached_short")),
        "live": is_live_upload(v),
        "completedLive": is_completed_broadcast(v)
    } for v in vids]
    force_rebuild=os.environ.get("ZT_FORCE_SYNC","").lower()=="true"
    if previous and new_state==previous and not force_rebuild:
        print("No YouTube video/playlist changes; skipping HTML regeneration.")
        return

    update_home(vids,short_ids)
    for n in ["recensioni","test","unboxing","gaming","analogiktek"]:
        update_category(n,vids,short_ids)
    state_path.write_text(
        json.dumps(new_state,ensure_ascii=False,indent=2),
        encoding="utf-8"
    )

    # Public and compact homepage feed: videos, six+ Shorts and completed livestream archives.
    # Firebase intentionally excludes dotfiles (including the full .youtube-latest.json).
    visible_items=[
        {
            "id":v["id"],
            "title":v["snippet"]["title"],
            "publishedAt":v["snippet"]["publishedAt"],
            "category":classify(v) or "video",
            "short":(v["id"] in short_ids) or bool(v.get("_cached_short")),
            "live":is_live_upload(v),
            "completedLive":is_completed_broadcast(v)
        }
        for v in vids
        if not is_live_upload(v)
    ][:200]
    Path("home-video-feed.json").write_text(
        json.dumps(visible_items,ensure_ascii=False,indent=2)+"\n",
        encoding="utf-8"
    )

if __name__=="__main__": main()
