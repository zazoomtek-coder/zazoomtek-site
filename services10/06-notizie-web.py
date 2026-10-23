#!/usr/bin/env python3
"""Render Notizie dal web: one lead on left, four small right, no 'Vedi tutte'.

Only this section's HTML/CSS/placement is edited. It keeps the approved
source list and does not touch YouTube, highlights, articles or review cards.
"""
import html
import json
import re
import hashlib
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
STYLE_ID="zt-services10-webnews-layout"
SCRIPT_ID="zt-services10-webnews-place"

STYLE='''<style id="zt-services10-webnews-layout">
#zt-webnews-home{clear:both;margin:18px 0;border:1px solid #ddd;border-radius:0;background:white}
#zt-webnews-home .zt-webnews-head{background:#1e1e1e;color:white;min-height:46px}
#zt-webnews-home .zt-webnews-head h2{color:white;background:#d51232;display:inline-block;margin:0;padding:13px 18px;font:900 15px/1.3 Arial,sans-serif}
#zt-webnews-home .zt-webnews-grid{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,1fr);grid-template-rows:repeat(4,minmax(95px,auto));gap:0;padding:9px}
#zt-webnews-home .zt-webnews-item{display:grid;grid-template-columns:94px minmax(0,1fr);align-items:center;gap:10px;padding:8px;border-bottom:1px solid #eee;text-decoration:none;min-width:0}
#zt-webnews-home .zt-webnews-item img{width:94px;height:78px;object-fit:cover}
#zt-webnews-home .zt-webnews-item:first-child{grid-column:1;grid-row:1/5;display:block;padding:5px 13px 8px 5px;border-right:1px solid #eee;border-bottom:0}
#zt-webnews-home .zt-webnews-item:first-child img{width:100%;height:auto;aspect-ratio:16/9;object-fit:cover}
#zt-webnews-home .zt-webnews-item:first-child .zt-webnews-info{display:block;margin:9px 3px}
#zt-webnews-home .zt-webnews-item:first-child strong{font-size:18px;line-height:1.35}
#zt-webnews-home .zt-webnews-item:first-child .zt-webnews-excerpt{display:block;color:#666;font-size:13px;line-height:1.45;margin:7px 0}
#zt-webnews-home .zt-webnews-item:not(:first-child) .zt-webnews-excerpt{display:none}
@media(max-width:650px){#zt-webnews-home .zt-webnews-grid{display:flex;flex-direction:column}
#zt-webnews-home .zt-webnews-item:first-child{border-right:0;border-bottom:1px solid #eee}
#zt-webnews-home .zt-webnews-item:first-child img{height:auto}}
</style>'''
SCRIPT='''<script id="zt-services10-webnews-place">
(function(){
  function place(){
    const block=document.getElementById("zt-webnews-home");
    const videoExplorer=document.querySelector(".ztp-top-videos");
    if(!block||!videoExplorer||!videoExplorer.parentNode)return false;
    if(block.previousElementSibling!==videoExplorer)
      videoExplorer.insertAdjacentElement("afterend",block);
    return true;
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",place);
  else place();
  const observer=new MutationObserver(function(){if(place())observer.disconnect()});
  observer.observe(document.documentElement,{childList:true,subtree:true});
  setTimeout(function(){observer.disconnect()},15000);
})();
</script>'''

FEEDS=(
    ("HDblog","https://www.hdblog.it/feed/"),
    ("Tom's Hardware Italia","https://www.tomshw.it/feed"),
    ("SmartWorld","https://www.smartworld.it/feed"),
    ("DDAY.it","https://www.dday.it/rss"),
    ("Tom's Hardware Italia","https://www.tomshw.it/feed/videogioco"),
)
def parse_feed(data:bytes,source:str)->list[dict]:
    root=ET.fromstring(data);found=[]
    for node in root.iter():
        if node.tag.rsplit("}",1)[-1] not in ("item","entry"):continue
        vals={}
        for child in node:
            name=child.tag.rsplit("}",1)[-1]
            vals.setdefault(name,child.text or "")
            if name=="link" and not vals[name]:
                vals[name]=child.attrib.get("href","")
        title=str(vals.get("title") or "").strip()
        url=str(vals.get("link") or "").strip()
        if not title or not url.startswith("https://"):continue
        image=""
        for child in node.iter():
            name=child.tag.rsplit("}",1)[-1]
            if name not in ("thumbnail","enclosure","content"):continue
            candidate=child.attrib.get("url","")
            if candidate.startswith("https://") and (
                name=="thumbnail" or "image/" in child.attrib.get("type","")
                or child.attrib.get("medium")=="image"):
                image=candidate;break
        summary=str(vals.get("description") or vals.get("summary") or "")
        if not image:
            m=re.search(r'<img[^>]*src=["\x27](https://[^"\x27]+)',summary,re.I)
            if m:image=html.unescape(m.group(1))
        excerpt=html.unescape(re.sub(r"<[^>]+>"," ",summary))
        excerpt=re.sub(r"\s+"," ",excerpt).strip()[:190]
        date=str(vals.get("pubDate") or vals.get("published") or vals.get("updated") or "")
        try:date=parsedate_to_datetime(date).astimezone(timezone.utc).isoformat()
        except (ValueError,TypeError,AttributeError):pass
        found.append({"id":hashlib.sha1(url.encode()).hexdigest()[:20],
            "source":source,"url":url,"title":title,"original_title":title,
            "published":date,"excerpt":excerpt,"image":image})
    return found

def refresh_rss(root:Path=ROOT,fetch=None,now=None):
    file=root/"notizie-dal-web.json"
    try:old=json.loads(file.read_text(encoding="utf-8"))
    except (OSError,ValueError):return 0
    now=now or datetime.now(timezone.utc)
    try:
        last=datetime.fromisoformat(str(old.get("updated_at","")).replace("Z","+00:00"))
        if now-last<timedelta(hours=24):return 0
    except (TypeError,ValueError):pass
    def download(url):
        req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req,timeout=15) as response:
            return response.read()
    fetch=fetch or download
    incoming=[]
    for source,url in FEEDS:
        try:incoming.extend(parse_feed(fetch(url),source))
        except Exception as exc:
            print("RSS source temporarily unavailable:",source,str(exc)[:100])
    unique={}
    for article in incoming:
        unique[article["url"]]=article
    fresh=sorted(unique.values(),key=lambda x:x.get("published",""),reverse=True)
    seen=set(unique)
    previous={i.get("url"):i for i in old.get("items",[]) if isinstance(i,dict)}
    for item in fresh:
        if not item.get("image"):
            item["image"]=previous.get(item["url"],{}).get("image","")
    for item in old.get("items",[]):
        if isinstance(item,dict) and item.get("url") not in seen:
            fresh.append(item);seen.add(item["url"])
    fresh=[i for i in fresh if i.get("image")]
    if len(fresh)<5:return 0
    old["items"]=fresh[:5]
    old["updated_at"]=now.isoformat()
    file.write_text(json.dumps(old,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return 5

def panel(items):
    tiles=[]
    for item in items[:5]:
        if not isinstance(item,dict):continue
        url=str(item.get("url") or "")
        cover=str(item.get("image") or "")
        title=str(item.get("original_title") or item.get("title") or "")
        excerpt=str(item.get("excerpt") or "")
        origin=str(item.get("source") or "")
        if not url.startswith("https://") or not cover or not title:continue
        tiles.append('<a class="zt-webnews-item" href="'+html.escape(url,quote=True)+
            '" target="_blank" rel="noopener noreferrer"><img src="'+
            html.escape(cover,quote=True)+'" alt="'+html.escape(title,quote=True)+
            '" loading="lazy"><span class="zt-webnews-info"><small>'+
            html.escape(origin)+'</small><strong>'+html.escape(title)+
            '</strong><span class="zt-webnews-excerpt">'+html.escape(excerpt)+
            '</span></span></a>')
    return ('<section id="zt-webnews-home" class="zt-webnews-home" aria-label="NOTIZIE DAL WEB">'
        '<header class="zt-webnews-head"><h2>NOTIZIE DAL WEB</h2></header>'
        '<div class="zt-webnews-grid">'+''.join(tiles)+'</div></section>'),len(tiles)

def update(root:Path=ROOT,refresh:bool=False):
    if refresh:refresh_rss(root)
    news=root/"notizie-dal-web.json"
    home=root/"index.html"
    if not news.is_file() or not home.is_file():return 0
    try:items=json.loads(news.read_text(encoding="utf-8")).get("items",[])
    except (ValueError,AttributeError):return 0
    section,count=panel(items)
    if not count:return 0
    source=home.read_text(encoding="utf-8")
    pattern=r'<section\b[^>]*id="zt-webnews-home"[^>]*>[\s\S]*?</section>'
    source,n=re.subn(pattern,lambda _: section,source,count=1)
    if not n:return 0
    # Previous iterations had conflicting CSS and relocation scripts.
    for ident in ("zt-draft-webnews-center",STYLE_ID):
        source=re.sub(r'<style id="'+ident+r'">[\s\S]*?</style>',"",source)
    for ident in ("zt-draft-webnews-relocate",SCRIPT_ID):
        source=re.sub(r'<script id="'+ident+r'">[\s\S]*?</script>',"",source)
    source=source.replace("</head>",STYLE+"\n</head>",1)
    source=source.replace("</body>",SCRIPT+"\n</body>",1)
    home.write_text(source,encoding="utf-8")
    print("Notizie dal web:",count,"stories, one lead + four compact")
    return count

if __name__=="__main__":
    import sys
    update(refresh="--offline" not in sys.argv)
