#!/usr/bin/env python3
import json, os, re, urllib.parse, urllib.request
from pathlib import Path
from datetime import datetime

CHANNEL_ID="UCJs0ZT10hUiPRD0UZtUpI1Q"
API="https://www.googleapis.com/youtube/v3/"
KEY=os.environ["YOUTUBE_API_KEY"]

def get(endpoint, **params):
    params["key"]=KEY
    with urllib.request.urlopen(API+endpoint+"?"+urllib.parse.urlencode(params), timeout=30) as r:
        return json.load(r)

def uploads():
    c=get("channels",part="contentDetails",id=CHANNEL_ID)
    pl=c["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    p=get("playlistItems",part="snippet,contentDetails",playlistId=pl,maxResults=30)
    ids=[x["contentDetails"]["videoId"] for x in p["items"]]
    v=get("videos",part="snippet,contentDetails",id=",".join(ids))["items"]
    return sorted(v,key=lambda x:x["snippet"]["publishedAt"],reverse=True)

def sec(d):
    m=re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?",d or "")
    return (int(m.group(1) or 0)*3600+int(m.group(2) or 0)*60+int(m.group(3) or 0)) if m else 0

def classify(v):
    t=v["snippet"]["title"].lower()
    if any(x in t for x in ["unboxing","cosa c'è","cosa c’è"]): return "unboxing"
    if any(x in t for x in ["recensione","review"]): return "recensioni"
    if any(x in t for x in ["gameplay","ps5","xbox","nintendo","switch","gaming","warzone","battlefield","wolverine","taxi"]): return "gaming"
    return "test"

def card(v):
    s=v["snippet"]; vid=v["id"]; title=s["title"].replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")
    date=datetime.fromisoformat(s["publishedAt"].replace("Z","+00:00")).strftime("%d %b %Y")
    return f'''    <article class="video-card">
      <button type="button" data-video="{vid}" aria-label="Riproduci {title}">
        <img src="https://i.ytimg.com/vi/{vid}/maxresdefault.jpg" onerror="this.onerror=null;this.src='https://i.ytimg.com/vi/{vid}/hqdefault.jpg'" alt="{title}">
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
    chosen=[v for v in vids if classify(v)==name][:10]
    block='<section class="video-grid">\n'+"\n".join(card(v) for v in chosen)+'\n  </section>'
    p.write_text(h[:a]+block+h[b+10:],encoding="utf-8")

def main():
    vids=uploads()
    for n in ["recensioni","test","unboxing","gaming"]: update_category(n,vids)
    # Homepage is intentionally not rebuilt wholesale here: update-site.py will only
    # be extended after exact-block validation, avoiding accidental cross-card replacements.
    Path(".youtube-latest.json").write_text(json.dumps([{"id":v["id"],"title":v["snippet"]["title"],"publishedAt":v["snippet"]["publishedAt"],"category":classify(v),"short":sec(v["contentDetails"]["duration"])<=180} for v in vids[:30]],ensure_ascii=False,indent=2),encoding="utf-8")

if __name__=="__main__": main()
