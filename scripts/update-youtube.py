#!/usr/bin/env python3
import html, json, os, re, urllib.parse, urllib.request
from pathlib import Path
from datetime import datetime

CHANNEL_ID="UCJs0ZT10hUiPRD0UZtUpI1Q"
HANDLE="@ZazoomTek"
API="https://www.googleapis.com/youtube/v3/"
KEY=os.environ["YOUTUBE_API_KEY"]

def get(endpoint, **params):
    params["key"]=KEY
    with urllib.request.urlopen(API+endpoint+"?"+urllib.parse.urlencode(params), timeout=30) as r:
        return json.load(r)

def uploads():
    c=get("channels",part="contentDetails",id=CHANNEL_ID)
    pl=c["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    p=get("playlistItems",part="snippet,contentDetails",playlistId=pl,maxResults=50)
    ids=[x["contentDetails"]["videoId"] for x in p["items"]]
    v=get("videos",part="snippet,contentDetails",id=",".join(ids))["items"]
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

def classify(v):
    t=v["snippet"]["title"].lower()
    if any(x in t for x in ["unboxing","cosa c'è","cosa c’è"]): return "unboxing"
    if any(x in t for x in ["recensione","review"]): return "recensioni"
    if any(x in t for x in ["gameplay","ps5","xbox","nintendo","switch","gaming","warzone","battlefield","wolverine","taxi","tomb raider","legacy of atlantis"]): return "gaming"
    return "test"

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

def update_category(name, vids):
    p=Path(name+".html")
    if not p.exists(): return
    h=p.read_text(encoding="utf-8")
    a=h.find('<section class="video-grid">')
    if a<0:return
    b=h.find("</section>",a)
    if b<0:return
    chosen=[v for v in vids if classify(v)==name][:20]
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

def update_home(vids, short_ids):
    p=Path("index.html")
    h=p.read_text(encoding="utf-8")

    # Main featured: newest long-form video only. Shorts never enter the large box.
    # Prefer the channel Shorts shelf; use duration as a fallback when that shelf
    # cannot be read. This change is intentionally isolated to the main feature.
    # Main feature: newest true 16:9 long-form upload, regardless of category.
    # Shorts/vertical videos never enter the large box.
    def is_true_longform(v):
        if v["id"] in short_ids:
            return False
        # YouTube Shorts can be up to 3 minutes. When the Shorts shelf cannot
        # identify an upload, avoid treating <=180s uploads as long-form.
        if not short_ids and sec(v["contentDetails"]["duration"])<=180:
            return False
        return True
    main_video=next((v for v in vids if is_true_longform(v)), None)
    if main_video:
        a=h.find('<article class="feature-main">')
        if a>=0:
            b=h.find("</article>",a)
            if b>=0: h=h[:a]+feature_main(main_video)+h[b+10:]

    # Side cards: newest item in each category, matched by category link anchor.
    for name in ["recensioni","test","unboxing","gaming"]:
        latest=next((v for v in vids if classify(v)==name),None)
        if latest:
            h=replace_article_containing(h,f'href="{name}.html" aria-label="Apri tutti',feature_side(latest,name))

    # Lower category thumbnails: exact box by data-page.
    for name in ["recensioni","test","unboxing","gaming"]:
        latest=next((v for v in vids if classify(v)==name),None)
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

    # Cache-busting build marker.
    h=re.sub(r'<meta name="zazoomtek-build" content="[^"]*">',
             f'<meta name="zazoomtek-build" content="{vids[0]["id"]}-{vids[0]["snippet"]["publishedAt"]}">',h,count=1)
    p.write_text(h,encoding="utf-8")

def main():
    vids=uploads()
    short_ids=youtube_short_ids()
    update_home(vids,short_ids)
    for n in ["recensioni","test","unboxing","gaming"]:
        update_category(n,vids)
    Path(".youtube-latest.json").write_text(
        json.dumps([{
            "id":v["id"],
            "title":v["snippet"]["title"],
            "publishedAt":v["snippet"]["publishedAt"],
            "category":classify(v),
            "short": (v["id"] in short_ids) if short_ids else sec(v["contentDetails"]["duration"])<=180
        } for v in vids[:30]],ensure_ascii=False,indent=2),
        encoding="utf-8"
    )

if __name__=="__main__": main()
