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
/* Sora-style editorial layout supplied by the editor: hero left, four rows right. */
#zt-webnews-home{box-sizing:border-box;width:100%;max-width:100%;min-width:0;clear:both;margin:18px 0 20px;border:0;border-radius:0;background:#fff;overflow:hidden}
#zt-webnews-home *{box-sizing:border-box}
#zt-webnews-home .zt-webnews-head{height:52px;display:flex;align-items:stretch;justify-content:space-between;background:#171719;color:#fff;border-radius:0}
#zt-webnews-home .zt-webnews-head h2{display:flex;align-items:center;margin:0;padding:0 17px;background:transparent;color:#fff;font:900 clamp(15px,1.45vw,19px)/1.15 Arial,Helvetica,sans-serif;letter-spacing:.025em;border-radius:0!important;clip-path:none!important}
#zt-webnews-home .zt-webnews-all{display:flex;align-items:center;justify-content:center;padding:0 20px;background:#f6525d;color:#fff;text-decoration:none;font:700 13px Arial,Helvetica,sans-serif}
#zt-webnews-home .zt-webnews-all:hover,#zt-webnews-home .zt-webnews-all:focus-visible{background:#d51232;color:white}
#zt-webnews-home .zt-webnews-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:clamp(16px,2.5vw,28px);padding:clamp(14px,2vw,24px) 0;align-items:stretch}
#zt-webnews-home .zt-webnews-item{min-width:0;display:grid;grid-template-columns:minmax(88px,37%) minmax(0,1fr);align-items:start;gap:clamp(9px,1.2vw,16px);color:#171719;text-decoration:none;overflow:hidden}
#zt-webnews-home .zt-webnews-item:not(:first-child){grid-column:2;align-self:start}
#zt-webnews-home .zt-webnews-item img{display:block;width:100%;height:auto;aspect-ratio:1.52;object-fit:cover;border-radius:0}
#zt-webnews-home .zt-webnews-info{min-width:0;display:flex;flex-direction:column;gap:7px}
#zt-webnews-home .zt-webnews-item strong{display:block;margin:0;color:#18191b;font:800 clamp(13px,1.15vw,18px)/1.32 Arial,Helvetica,sans-serif;overflow-wrap:anywhere}
#zt-webnews-home .zt-webnews-date{color:#8d8d8d;font:400 clamp(11px,.96vw,14px)/1.35 Arial,Helvetica,sans-serif}
#zt-webnews-home .zt-webnews-item:first-child{grid-column:1;grid-row:1 / span 4;display:block}
#zt-webnews-home .zt-webnews-item:first-child img{aspect-ratio:1.99;object-fit:cover}
#zt-webnews-home .zt-webnews-item:first-child .zt-webnews-category{display:inline-block;margin-top:-27px;position:relative;padding:7px 12px;background:#f6525d;color:white;font:700 12px Arial,sans-serif}
#zt-webnews-home .zt-webnews-item:first-child strong{margin:12px 0 9px;font:900 clamp(21px,2vw,30px)/1.18 Arial,Helvetica,sans-serif}
#zt-webnews-home .zt-webnews-item:first-child .zt-webnews-date{font-size:clamp(12px,1.04vw,15px)}
#zt-webnews-home .zt-webnews-excerpt{display:none;color:#777;font:400 clamp(13px,1.2vw,17px)/1.48 Arial,Helvetica,sans-serif}
#zt-webnews-home .zt-webnews-item:first-child .zt-webnews-excerpt{display:block;margin-top:12px}
#zt-webnews-home .zt-webnews-item:not(:first-child) .zt-webnews-category{display:none}
#zt-webnews-home .zt-webnews-item:hover strong{color:#d51232}
@media(max-width:820px){#zt-webnews-home .zt-webnews-grid{gap:18px}#zt-webnews-home .zt-webnews-item{grid-template-columns:39% 1fr}#zt-webnews-home .zt-webnews-item:first-child img{aspect-ratio:16/9}}
@media(max-width:640px){#zt-webnews-home .zt-webnews-grid{display:flex;flex-direction:column;gap:16px;padding:14px 0}#zt-webnews-home .zt-webnews-item:first-child{border-bottom:1px solid #e7e7e7;padding-bottom:16px}#zt-webnews-home .zt-webnews-item:not(:first-child){gap:12px}#zt-webnews-home .zt-webnews-item:first-child strong{font-size:23px}#zt-webnews-home .zt-webnews-all{padding:0 13px}}
</style>'''
SCRIPT='''<script id="zt-services10-webnews-place">
(function(){
  "use strict";
  function place(){
    const block=document.getElementById("zt-webnews-home");
    const videoShelves=document.getElementById("zt-home-shelves");
    // ESPLORA ULTIMI VIDEO is the full video shelf, not .ztp-top-videos
    // (that other class denotes latest VIDEO REVIEWS).
    if(!block||!videoShelves||!videoShelves.parentElement)return false;
    const parent=videoShelves.parentElement;
    if(block.parentElement!==parent||block.previousElementSibling!==videoShelves)
      videoShelves.insertAdjacentElement("afterend",block);
    block.style.width="100%";
    block.style.maxWidth="100%";
    block.style.boxSizing="border-box";
    return true;
  }
  function init(){
    if(place())return;
    const observer=new MutationObserver(function(){if(place())observer.disconnect()});
    observer.observe(document.documentElement,{childList:true,subtree:true});
    setTimeout(function(){observer.disconnect()},15000);
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init,{once:true});
  else init();
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

def date_label(raw):
    try:
        moment=datetime.fromisoformat(str(raw).replace("Z","+00:00"))
        return moment.strftime("%d/%m/%Y")
    except (ValueError, TypeError, AttributeError):
        try:return parsedate_to_datetime(str(raw)).strftime("%d/%m/%Y")
        except (ValueError, TypeError, AttributeError):return ""

def eligible(items):
    result=[];seen_urls=set();seen_titles=set()
    for item in items:
        if not isinstance(item,dict):continue
        url=str(item.get("url") or "").strip()
        cover=str(item.get("image") or "").strip()
        title=str(item.get("original_title") or item.get("title") or "").strip()
        normalized=re.sub(r"\s+"," ",title).casefold()
        if (not url.startswith("https://") or not cover or not title or
                url in seen_urls or normalized in seen_titles):continue
        seen_urls.add(url);seen_titles.add(normalized)
        result.append(item)
    return result

def panel(items):
    tiles=[]
    for item in eligible(items)[:5]:
        url=html.escape(str(item["url"]),quote=True)
        cover=html.escape(str(item["image"]),quote=True)
        title=html.escape(str(item.get("original_title") or item.get("title") or ""))
        excerpt=html.escape(str(item.get("excerpt") or ""))
        origin=html.escape(str(item.get("source") or "News"))
        date=html.escape(date_label(item.get("published") or ""))
        tiles.append('<a class="zt-webnews-item" href="'+url+
          '" target="_blank" rel="noopener noreferrer"><span class="zt-webnews-media">'+
          '<img src="'+cover+'" alt="'+title+'" loading="lazy"></span>'+
          '<span class="zt-webnews-info"><span class="zt-webnews-category">'+origin+
          '</span><strong>'+title+'</strong><span class="zt-webnews-date">'+date+
          '</span><span class="zt-webnews-excerpt">'+excerpt+'</span></span></a>')
    return ('<section id="zt-webnews-home" class="zt-webnews-home" aria-label="Notizie dal web">'
        '<header class="zt-webnews-head"><h2>NOTIZIE DAL WEB</h2>'
        '<a class="zt-webnews-all" href="/notizie-dal-web.html">VEDI TUTTE</a></header>'
        '<div class="zt-webnews-grid">'+''.join(tiles)+'</div></section>'),len(tiles)

def render_archive(items):
    rows=[]
    for item in eligible(items):
        title=html.escape(str(item.get("original_title") or item.get("title") or ""))
        link=html.escape(str(item["url"]),quote=True)
        source=html.escape(str(item.get("source") or ""))
        stamp=html.escape(date_label(item.get("published") or ""))
        rows.append('<article class="zt-webarchive-story"><h2><a href="'+link+
          '" target="_blank" rel="noopener noreferrer">'+title+'</a></h2>'+
          '<p>'+source+' · '+stamp+'</p></article>')
    return ('<!doctype html><html lang="it"><head><meta charset="utf-8">'
      '<meta name="viewport" content="width=device-width, initial-scale=1">'
      '<title>Notizie dal web | ZazoomTek</title>'
      '<meta name="description" content="Selezione di notizie tecnologia e gaming da fonti esterne">'
      '<link rel="stylesheet" href="/zt-design.css">'
      '<style>body{font-family:Arial,sans-serif;background:#eee;color:#202020;margin:0}'
      'main{max-width:1080px;margin:28px auto;background:white;padding:24px}'
      'header{background:#171719;padding:18px 24px}header a{color:white;font-weight:900}'
      'h1{border-left:8px solid #d51232;padding-left:15px}'
      '.zt-webarchive-story{padding:17px 0;border-bottom:1px solid #eee}'
      '.zt-webarchive-story a{color:#171719;text-decoration:none}'
      '.zt-webarchive-story a:hover{color:#d51232}'
      '.zt-webarchive-story p{color:#888;font-size:13px}'
      '</style></head><body><header><a href="/">ZazoomTek · Home</a></header>'
      '<main><h1>NOTIZIE DAL WEB</h1><p>Rassegna stampa da fonti esterne.</p>'
      +''.join(rows)+'</main></body></html>')

def update(root:Path=ROOT,refresh:bool=False):
    if refresh:refresh_rss(root)
    news=root/"notizie-dal-web.json"
    home=root/"index.html"
    if not news.is_file() or not home.is_file():return 0
    try:items=json.loads(news.read_text(encoding="utf-8")).get("items",[])
    except (ValueError,AttributeError):return 0
    section,count=panel(items)
    if not count:return 0
    archive=root/"notizie-dal-web.html"
    archive.write_text(render_archive(items),encoding="utf-8")
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
