#!/usr/bin/env python3
"""RSS-only external news snapshot for ZazoomTek. No independent releases.
Run ONLY inside the existing scheduled Master publication, not its 5-min polls.
All five official technology RSS sources configured and enabled.
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from io import BytesIO
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlparse, urljoin
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
STATE=Path("notizie-dal-web.json")
ASSETS=Path("assets/notizie-dal-web")
SOURCES=(
  ("HDblog","https://www.hdblog.it/feed/","hdblog.it",True),
  ("Tom's Hardware Italia","https://www.tomshw.it/feed/","tomshw.it",True),
  ("DDAY.it","https://www.dday.it/rss","dday.it",True),
  ("Wired Italia","https://www.wired.it/feed/rss","wired.it",True),
  ("SmartWorld","https://www.smartworld.it/feed","smartworld.it",True),
)
assert len(SOURCES)==5

class Plain(HTMLParser):
    def __init__(self):super().__init__();self.words=[]
    def handle_data(self,d):self.words.append(d)
def plain(value):
    p=Plain()
    try:p.feed(str(value or "")[:12000])
    except Exception:return ""
    return " ".join(unescape(" ".join(p.words)).split())

def date_of(value):
    if not value:return datetime(1970,1,1,tzinfo=timezone.utc)
    try:d=parsedate_to_datetime(value)
    except Exception:
        try:d=datetime.fromisoformat(value.replace("Z","+00:00"))
        except Exception:return datetime(1970,1,1,tzinfo=timezone.utc)
    if d.tzinfo is None:d=d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)

def tag(node,name):
    for x in node:
        if x.tag.split("}")[-1]==name:return (x.text or "").strip()
    return ""

def parse_feed(data,source,domain):
    root=ET.fromstring(data)
    rows=[]
    for n in root.iter():
        if n.tag.split("}")[-1] not in {"item","entry"}:continue
        original=plain(tag(n,"title"))
        link=tag(n,"link")
        if not link:
            for x in n:
                if x.tag.split("}")[-1]=="link" and x.attrib.get("href"):
                    link=x.attrib["href"];break
        link=link.strip()
        u=urlparse(link)
        if u.scheme!="https" or not (u.hostname==domain or u.hostname.endswith("."+domain)):continue
        if not original or len(original)<12 or len(link)>1100:continue
        guid=tag(n,"guid") or tag(n,"id") or link
        pub=date_of(tag(n,"pubDate") or tag(n,"published") or tag(n,"updated") or tag(n,"date"))
        description=plain(tag(n,"description") or tag(n,"summary") or tag(n,"content"))
        img=""
        for x in n.iter():
            typ=x.tag.split("}")[-1]
            if typ in ("thumbnail","content","enclosure"):
                u=x.attrib.get("url","")
                if u.lower().startswith("https://") and (typ!="content" or x.attrib.get("medium")=="image" or x.attrib.get("type","").startswith("image/")):
                    img=u;break
        if not img:
            m=re.search(r'<img\b[^>]*\bsrc=["\'](https://[^"\']+)',tag(n,"description") or "",re.I)
            if m:img=m.group(1)
        rows.append({"id":hashlib.sha256((source+"|"+guid+"|"+link).encode()).hexdigest()[:20],
                     "source":source,"url":link,"original":original,"description":description,
                     "published":pub.isoformat(),"image_candidate":img})
    return sorted(rows,key=lambda x:x["published"],reverse=True)[:30]

STOP={"come","che","con","del","della","delle","degli","dello","sono","dopo","per","una","uno","gli","dai","tra","alla","sul","sulla","nelle","nuovo","nuova","tutte","tutti","sua","piu","più","questo","questa","anche","loro","dei","dell","nelle","della","dei","nel","non","the","and"}
def restate(original):
    cleaned=re.sub(r"[\[\]{}|:;.!?–—«»“”\"']"," ",original)
    words=[w for w in re.findall(r"[\wÀ-ÿ+.-]+",cleaned) if len(w)>2 and w.lower() not in STOP]
    topic=" ".join(words[:7]).strip()
    if len(topic)<7:topic="innovazione e tecnologia"
    return "Il punto su "+topic[:88].rstrip(" ,.;")
def excerpt(row):
    # Deliberately do NOT mirror a feed description or reproduce article text.
    words=[w for w in re.findall(r"[\wÀ-ÿ+.-]+",row["original"]) if len(w)>3 and w.lower() not in STOP][:5]
    topic=" ".join(words) or "tecnologia"
    return f"La notizia riguarda {topic}. {row['source']} pubblica l'aggiornamento originale, con dettagli e contesto consultabili direttamente alla fonte."

def safe_fetch(url,domain,max_size=1600000,timeout=10):
    req=Request(url,headers={"User-Agent":"ZazoomTekRSS/1.0 (+https://zazoomtek.it; news aggregation)","Accept":"application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9"})
    with urlopen(req,timeout=timeout) as res:
        final=urlparse(res.url)
        if final.scheme!="https" or not (final.hostname==domain or final.hostname.endswith("."+domain)):
            raise ValueError("Unexpected RSS redirect host")
        data=res.read(max_size+1)
        if len(data)>max_size:raise ValueError("RSS too large")
        return data

def image_for(row,root):
    """Only permissioned imagery may be rehosted. Else original WebP art."""
    from PIL import Image, ImageDraw
    seed=int(row["id"][:12],16)
    tones=[(28,38,57),(24,46,61),(50,38,54),(33,47,43),(46,37,51)]
    w,h=720,405
    image=Image.new("RGB",(w,h),tones[seed%len(tones)])
    draw=ImageDraw.Draw(image)
    for i in range(15):
        x=(seed//(i+7)+i*91)%900-90
        y=(seed//(i+11)+i*73)%550-80
        radius=40+(seed+i*31)%140
        color=(min(170,53+i*4),min(137,70+i*3),min(150,92+i*2))
        draw.ellipse((x,y,x+radius,y+radius),fill=color,width=2)
    draw.rectangle((0,0,16,h),fill=(213,18,50))
    draw.rectangle((0,h-70,w,h),fill=(19,23,31))
    # Own graphic: neither hotlink nor copy an unlicensed editorial photo.
    draw.text((33,h-47),"NOTIZIE DAL WEB",fill=(245,245,248))
    return image

TECH_TERMS=(
 "android","iphone","ipad","ios","macbook","apple watch","samsung","google","microsoft",
 "windows","linux","xbox","playstation","ps5","ps4","nintendo","videogioch",
 "gaming","gpu","cpu","ram ","dram","ssd","nvme","ryzen","geforce","rtx",
 "snapdragon","nvidia","amd ","intel","computer","laptop","notebook","alienware",
 "hardware","software","digitale","tecnologia","tech","cyber","sicurezza informatica",
 "intelligenza artificiale","robot","smartphone","tablet","cloud","data center",
 "elettronic","microfono","insta360","fotocamera","camera","televis","display","wifi",
 "wi-fi","bluetooth","router","app ","domotica","openai","ai agent","startup",
 "chip","processore","social media","facebook","instagram","tiktok","whatsapp",
 "streaming","netflix","amazon luna","prime video","meta quest","occhiali smart")
PROMOTIONAL=("offerta","sconto","offerte","coupon","codice sconto","buono amazon",
 "prezzo stracciato","prezzo mai visto","super prezzo","a meno di","ultimi pezzi",
 "codice promozionale","svendita","black friday","pochi pezzi","ultime unità","pezzi rimasti","solo oggi","in promozione","scontat","volantino","prezzo bomba","prezzo shock","spendi meno","risparmia","costa solo")
def relevant(row,now=None):
    title=row["original"].lower()
    if any(x in title for x in PROMOTIONAL):return False
    if not any(t in title for t in TECH_TERMS):return False
    stamp=datetime.fromisoformat(row["published"])
    now=now or datetime.now(timezone.utc)
    return now-timedelta(days=14)<=stamp<=now+timedelta(days=1)

def choose(candidates,old):
    pool={}
    for row in candidates:
        if row["source"] not in pool:pool[row["source"]]=[]
        if row["url"] not in {a["url"] for a in pool[row["source"]]}:pool[row["source"]].append(row)
    chosen=[]
    # One per available source first, then recency-balanced additional items.
    while len(chosen)<5 and any(pool.values()):
        round_items=[]
        for name,*_ in SOURCES:
            if pool.get(name):
                round_items.append(pool[name].pop(0))
        for r in sorted(round_items,key=lambda x:x["published"],reverse=True):
            if len(chosen)<5:chosen.append(r)
    if len(chosen)<5:return None
    selected={r["id"] for r in chosen}
    previous={r.get("id") for r in old.get("items",[])}
    if selected==previous:return None
    return chosen

def update(root=ROOT,fetch=safe_fetch):
    old_path=root/STATE
    try:old=json.loads(old_path.read_text(encoding="utf-8"))
    except (FileNotFoundError,ValueError):old={"version":1,"items":[]}
    candidates=[];ok=[]
    for source,url,domain,enabled in SOURCES:
        if not enabled:
            print("SKIP source disabled:",source)
            continue
        try:
            rows=parse_feed(fetch(url,domain),source,domain)
            if not rows:raise ValueError("RSS returned no usable article links")
            candidates.extend([row for row in rows if relevant(row)]);ok.append(source)
            print("RSS",source,":",len(rows),"items")
        except Exception as e:
            print("RSS unavailable",source,":",str(e)[:180])
    # Do not replace 5 valid stories with a smaller or failed snapshot.
    if len(ok)<3 or len(candidates)<5:
        print("WEB-NEWS UNCHANGED: insufficient valid feeds; preserve existing published state")
        return []
    selected=choose(candidates,old)
    if selected is None:
        print("WEB-NEWS UNCHANGED: same story IDs, no new thumbnails or commits")
        return []
    folder=root/ASSETS;folder.mkdir(parents=True,exist_ok=True)
    new=[];changed=[]
    for row in selected:
        name=row["id"]+".webp";dest=folder/name
        if not dest.exists():
            # Never download/rehost an editorial image without an explicit license.
            image_for(row,root).save(dest,"WEBP",quality=80,method=5)
            changed.append(str(ASSETS/name))
        new.append({"id":row["id"],"source":row["source"],"url":row["url"],
                    "title":restate(row["original"]),"excerpt":excerpt(row)[:270],
                    "published":row["published"],"image":"/"+str(ASSETS/name)})
    output={"version":1,"updated_at":datetime.now(timezone.utc).isoformat(),
            "license_policy":"Five approved RSS publishers; external editorial photographs require an explicit redistribution license",
            "items":new}
    old_path.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    changed.append(str(STATE))
    print("WEB-NEWS UPDATED:",len(new),"stories,",len(changed)-1,"new original WebP thumbnails")
    return changed

def self_test():
    rss=b'<rss><channel><item><title>Nuovi strumenti per il settore tecnologico</title><link>https://www.hdblog.it/news/2026/test/</link><guid>test-1</guid><pubDate>Thu, 22 Oct 2026 12:00:00 GMT</pubDate></item></channel></rss>'
    rows=parse_feed(rss,"HDblog","hdblog.it")
    assert len(rows)==1 and rows[0]["source"]=="HDblog"
    assert not parse_feed(rss.replace(b"hdblog.it",b"evil.test"),"HDblog","hdblog.it")
    assert len(excerpt(rows[0]).split())<=50
    assert choose(rows,{"items":[]}) is None
    assert not relevant({"original":"Le migliori tende da campeggio per famiglie","published":"2026-10-22T10:00:00+00:00"},datetime(2026,10,22,tzinfo=timezone.utc))
    assert relevant({"original":"Nvidia GeForce RTX 5050 e nuove GPU","published":"2026-10-22T10:00:00+00:00"},datetime(2026,10,22,tzinfo=timezone.utc))
    print("PASS: RSS parser, source whitelist, 5-item guard and original excerpts")
if __name__=="__main__":
    if "--self-test" in sys.argv:self_test()
    else:print(json.dumps({"paths":update()},ensure_ascii=False))
