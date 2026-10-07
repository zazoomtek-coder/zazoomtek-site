#!/usr/bin/env python3
import html, json, os, re, urllib.parse, urllib.request
from pathlib import Path
from datetime import datetime

CHANNEL_ID="UCJs0ZT10hUiPRD0UZtUpI1Q"
HANDLE="@ZazoomTek"
API="https://www.googleapis.com/youtube/v3/"
KEY=os.environ["YOUTUBE_API_KEY"]
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

def get(endpoint, **params):
    params["key"]=KEY
    with urllib.request.urlopen(API+endpoint+"?"+urllib.parse.urlencode(params), timeout=30) as r:
        return json.load(r)

def uploads():
    c=get("channels",part="contentDetails",id=CHANNEL_ID)
    pl=c["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    ids=[]
    token=None
    while True:
        params={"part":"snippet,contentDetails","playlistId":pl,"maxResults":50}
        if token: params["pageToken"]=token
        p=get("playlistItems",**params)
        ids.extend(x["contentDetails"]["videoId"] for x in p.get("items",[]))
        token=p.get("nextPageToken")
        if not token: break
    v=[]
    for i in range(0,len(ids),50):
        v.extend(get("videos",part="snippet,contentDetails,liveStreamingDetails",id=",".join(ids[i:i+50]))["items"])
    return sorted(v,key=lambda x:x["snippet"]["publishedAt"],reverse=True)

def sec(d):
    m=re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?",d or "")
    return (int(m.group(1) or 0)*3600+int(m.group(2) or 0)*60+int(m.group(3) or 0)) if m else 0

def is_live_upload(v):
    # Exclude live streams (past, current or scheduled) from the Home "Ultimi Video".
    # YouTube keeps liveStreamingDetails on completed live broadcasts too.
    live_state=(v.get("snippet",{}).get("liveBroadcastContent") or "none").lower()
    return live_state in ("live","upcoming") or bool(v.get("liveStreamingDetails"))

def youtube_short_ids():
    # YouTube Data API doesn't expose a direct isShort flag.
    # Read the channel Shorts shelf and use duration only as a fallback.
    try:
        req=urllib.request.Request(
            f"https://www.youtube.com/{HANDLE}/shorts",
            headers={"User-Agent":"Mozilla/5.0"}
        )
        with urllib.request.urlopen(req,timeout=30) as r:
            page=r.read().decode("utf-8","ignore")
        ids=set(re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"',page))
        ids.update(re.findall(r'/shorts/([A-Za-z0-9_-]{11})',page))
        return ids
    except Exception:
        return set()

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

def classify(v):
    if v["id"] in TEST_VIDEO_IDS: return "test"
    if v["id"] in GAMING_VIDEO_IDS: return "gaming"
    if v["id"] in UNBOXING_VIDEO_IDS: return "unboxing"
    if v["id"] in REVIEWS_VIDEO_IDS: return "recensioni"
    if v["id"] in ANALOGIKTEK_VIDEO_IDS: return "analogiktek"
    return None

def esc(s): return html.escape(s,quote=True)

def card(v):
    s=v["snippet"]; vid=v["id"]; title=esc(s["title"])
    date=datetime.fromisoformat(s["publishedAt"].replace("Z","+00:00")).strftime("%d %b %Y")
    return f'''    <article class="video-card">
      <button type="button" data-video="{vid}" aria-label="Riproduci {title}">
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


def sidebar_stack_card(v):
    vid=v["id"]; title=esc(v["snippet"]["title"])
    dt=datetime.fromisoformat(v["snippet"]["publishedAt"].replace("Z","+00:00"))
    months=["gennaio","febbraio","marzo","aprile","maggio","giugno","luglio","agosto","settembre","ottobre","novembre","dicembre"]
    date=f"{dt.day} {months[dt.month-1]} {dt.year}"
    return (
        f'          <article class="zt-stack-card">'
        f'<button class="video-thumb" data-video="{vid}" onclick="playVideo(this)">'
        f'<img src="https://i.ytimg.com/vi/{vid}/maxresdefault.jpg" '
        f'onerror="this.onerror=null;this.src=\'https://i.ytimg.com/vi/{vid}/hqdefault.jpg\'" '
        f'alt="{title}" loading="lazy"></button>'
        f'<div class="zt-stack-copy"><h3>{title}</h3><small>{date}</small></div></article>'
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
        if v["id"] in short_ids or is_live_upload(v):
            return False
        ratio=video_aspect_ratio(v)
        return ratio is not None and 1.70 <= ratio <= 1.82

    def is_true_vertical_short(v):
        if is_live_upload(v):
            return False
        ratio=video_aspect_ratio(v)
        if ratio is None or not (0.54 <= ratio <= 0.59):
            return False
        # Prefer YouTube's Shorts shelf. If that shelf cannot be read during
        # a run, a true 9:16 upload up to 3 minutes is a safe Shorts fallback.
        return v["id"] in short_ids or sec(v["contentDetails"]["duration"])<=180

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

    # The main Home carousel is now reserved for the latest written reviews
    # and is managed by update-youtube-posts.py. Keep the five newest landscape
    # video IDs only for sidebar de-duplication; do not rewrite the Home carousel.
    editorial_latest=[
        v for v in ordered
        if not is_live_upload(v) and is_true_landscape(v)
    ][:5]
    editorial_latest_ids={v["id"] for v in editorial_latest}

    # Unified Home sidebar: the six newest REAL 16:9 uploads,
    # strictly newest -> oldest. No Shorts, vertical clips or live streams.
    stack=[]
    for v in ordered:
        if is_true_landscape(v):
            stack.append(v)
            if len(stack)>=6:
                break

    h=replace_marker_block(
        h,"<!-- SIDEBAR_STACK_VIDEOS_START -->","<!-- SIDEBAR_STACK_VIDEOS_END -->",
        "\n".join(sidebar_stack_card(v) for v in stack)
    )
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
    vids=uploads()
    TEST_VIDEO_IDS=playlist_video_ids(TEST_PLAYLIST_ID)
    GAMING_VIDEO_IDS=playlist_video_ids(GAMING_PLAYLIST_ID)
    UNBOXING_VIDEO_IDS=playlist_video_ids(UNBOXING_PLAYLIST_ID)
    REVIEWS_VIDEO_IDS=playlist_video_ids(REVIEWS_PLAYLIST_ID)
    ANALOGIKTEK_VIDEO_IDS=playlist_video_ids(ANALOGIKTEK_PLAYLIST_ID)
    short_ids=youtube_short_ids()
    update_home(vids,short_ids)
    for n in ["recensioni","test","unboxing","gaming","analogiktek"]:
        update_category(n,vids,short_ids)
    Path(".youtube-latest.json").write_text(
        json.dumps([{
            "id":v["id"],
            "title":v["snippet"]["title"],
            "publishedAt":v["snippet"]["publishedAt"],
            "category":classify(v),
            "short": (v["id"] in short_ids) if short_ids else sec(v["contentDetails"]["duration"])<=180,
            "live": is_live_upload(v)
        } for v in vids],ensure_ascii=False,indent=2),
        encoding="utf-8"
    )

if __name__=="__main__": main()
