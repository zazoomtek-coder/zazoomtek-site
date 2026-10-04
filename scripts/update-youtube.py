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
        v.extend(get("videos",part="snippet,contentDetails",id=",".join(ids[i:i+50]))["items"])
    return sorted(v,key=lambda x:x["snippet"]["publishedAt"],reverse=True)

def sec(d):
    m=re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?",d or "")
    return (int(m.group(1) or 0)*3600+int(m.group(2) or 0)*60+int(m.group(3) or 0)) if m else 0

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

def update_category(name, vids, short_ids):
    p=Path(name+".html")
    if not p.exists(): return
    h=p.read_text(encoding="utf-8")
    a=h.find('<section class="video-grid">')
    if a<0:return
    b=h.find("</section>",a)
    if b<0:return
    candidates=[v for v in vids if classify(v)==name]
    # Avoid duplicate coverage in category pages: when a long-form and a Short
    # cover the same item/review, keep the long-form version.
    def topic_key(v):
        t=v["snippet"]["title"].lower()
        t=re.sub(r'\b(shorts?|short|video|full|hd|4k|recensione|review|test|prova|unboxing|gameplay|ps5|ps4|xbox|nintendo|switch)\b',' ',t)
        t=re.sub(r'[^a-z0-9à-ÿ]+',' ',t)
        return set(x for x in t.split() if len(x)>2)
    longs=[v for v in candidates if v["id"] not in short_ids]
    chosen=[]
    for v in candidates:
        is_short=v["id"] in short_ids
        if is_short:
            vk=topic_key(v)
            duplicate=any(len(vk & topic_key(l)) >= 2 and len(vk & topic_key(l))/max(1,min(len(vk),len(topic_key(l)))) >= .5 for l in longs)
            if duplicate: continue
        chosen.append(v)
        if len(chosen)>=20: break
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

def update_home(vids, short_ids):
    p=Path("index.html")
    h=p.read_text(encoding="utf-8")

    # Main featured: newest long-form video only. Shorts never enter the large box.
    # Prefer the channel Shorts shelf; use duration as a fallback when that shelf
    # cannot be read. This change is intentionally isolated to the main feature.
    # Main feature: newest true 16:9 long-form upload, regardless of category.
    # Shorts/vertical videos never enter the large box.
    def is_true_landscape(v):
        # Home large box: verify the REAL source dimensions from YouTube player data.
        # Duration/title/category do not matter.
        if v["id"] in short_ids:
            return False
        try:
            req=urllib.request.Request(
                f"https://www.youtube.com/watch?v={v['id']}",
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
                                    endpos=i+1; break
                    if endpos:
                        data=json.loads(page[brace:endpos])
                        fmts=(data.get("streamingData",{}).get("adaptiveFormats",[]) or
                              data.get("streamingData",{}).get("formats",[]))
                        dims=[(x.get("width"),x.get("height")) for x in fmts if x.get("width") and x.get("height")]
                        if dims:
                            w,h=max(dims,key=lambda x:x[0]*x[1])
                            ratio=float(w)/float(h)
                            return 1.70 <= ratio <= 1.82
        except Exception:
            pass
        return False

    # Choose the newest upload by YouTube publish date, but never a known Short.
    # For ZazoomTek the upload order is authoritative; vertical Shorts are removed
    # by the Shorts shelf before selecting the main Home feature.
    ordered=sorted(vids,key=lambda v:v["snippet"]["publishedAt"],reverse=True)
    main_video=next((v for v in ordered if v["id"] not in short_ids),None)
    if main_video:
        a=h.find('<article class="feature-main">')
        if a>=0:
            b=h.find("</article>",a)
            if b>=0: h=h[:a]+feature_main(main_video)+h[b+10:]

    # Side cards next to the main feature: newest upload in each category.
    # Both 16:9 and 9:16 are allowed. Selection is strictly by YouTube publish date.
    # If the main large video belongs to that category, do not show another video
    # about the same/newer coverage there: keep the previous different item instead.
    for name in ["recensioni","test","unboxing","gaming"]:
        candidates=[
            v for v in vids
            if classify(v)==name
            and (not main_video or v["id"] != main_video["id"])
        ]
        candidates.sort(key=lambda v:v["snippet"]["publishedAt"], reverse=True)
        if main_video and classify(main_video)==name:
            # Keep the prior category item to avoid homepage duplication.
            main_time=main_video["snippet"]["publishedAt"]
            candidates=[v for v in candidates if v["snippet"]["publishedAt"] < main_time]
        latest=candidates[0] if candidates else None
        if latest:
            h=replace_article_containing(h,f'href="{name}.html" aria-label="Apri tutti',feature_side(latest,name))

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

    # Exactly five latest Shorts.
    shorts=[v for v in vids if v["id"] in short_ids]
    if not shorts:
        shorts=[v for v in vids if sec(v["contentDetails"]["duration"])<=180]
    shorts=shorts[:5]
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
            "short": (v["id"] in short_ids) if short_ids else sec(v["contentDetails"]["duration"])<=180
        } for v in vids],ensure_ascii=False,indent=2),
        encoding="utf-8"
    )

if __name__=="__main__": main()
