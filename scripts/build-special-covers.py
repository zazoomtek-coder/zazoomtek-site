#!/usr/bin/env python3
"""Free, rights-conscious hero images for APPROVED special news only.

Search Wikimedia Commons for CC0/public-domain or attributed CC BY images, convert to light WebP
and store the original file page in a provenance manifest. If none pass the
checks or the network fails, draw original themed artwork locally with Pillow.
No API key, subscriptions or copying other publications' covers.
"""
import datetime as dt
import hashlib
import html
import io
import json
import math
import random
import re
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT=Path(__file__).resolve().parent.parent
APPROVED=ROOT/"approved-special-articles.json"
OUT=ROOT/"special-cover-manifest.json"
COVERS=ROOT/"assets"/"special"
COVERS.mkdir(parents=True,exist_ok=True)
SIZE=(1280,720)
MAX_BYTES=300_000
API="https://commons.wikimedia.org/w/api.php"
USER_AGENT="ZazoomTekEditorialCovers/1.0 (https://zazoomtek.it/contatti.html; rights-compliance)"
PALETTES=[
 ("#ec3851","#130d21"),("#f7a42e","#21120f"),
 ("#27ca8a","#092b27"),("#48bde9","#101f39"),
 ("#c873e4","#21112c"),("#eed64b","#202114"),
 ("#ff724e","#291421"),("#62b0ee","#172a3c"),
]
STOP_WORDS={"il","lo","la","gli","le","un","una","di","del","della","dei",
 "e","con","per","che","nel","nella","sulle","sui","delle","alla","anche",
 "come","contro","sotto","dopo","da","al","dei","tra","sul","un","europea",
 "europa","nuovo","nuova","digital","news","oggi"}
TOPICS=(
 (("bulgaria","digital services act","commissione europea"),"European Commission building"),
 (("hacker","cyber","attacchi","fbi"),"cybersecurity computer server"),
 (("anthropic","intelligenza artificiale","ai "," ia "), "computer data center"),
 (("occhiali","glasses"),"smart glasses"),
 (("diablo","call of duty","monete virtuali","acquisti in-game"),"video game controller"),
 (("minori","kids act","bambini"),"video games children"),
 (("energia","infrastrutture"),"power grid infrastructure"),
 (("privacy","dati personali"),"digital privacy technology"),
 (("videogiochi","gioco","gaming"),"video game controller"),
)

def shortname(item):
    return ("tech-impact" if item["section"]=="tech" else "gaming-inside")+"-"+item["slug"]
def request(url, limit):
    req=urllib.request.Request(url,headers={"User-Agent":USER_AGENT,"Accept":"application/json,image/*"})
    with urllib.request.urlopen(req,timeout=13) as response:
        length=int(response.headers.get("Content-Length") or "0")
        if length>limit:raise ValueError("File exceeds download limit")
        data=response.read(limit+1)
        if len(data)>limit:raise ValueError("File exceeds download limit")
        return data
def terms(item):
    explicit=item.get("cover_search")
    if isinstance(explicit,str) and 4<=len(explicit)<=75 and re.fullmatch(r"[\w\s'-]+",explicit):
        return explicit
    low=(item["title"]+" "+item.get("summary","")).lower()
    for triggers,term in TOPICS:
        if any(x in low for x in triggers):
            return term
    words=[w for w in re.findall(r"[a-zà-ÿ]{4,}",low) if w not in STOP_WORDS]
    return " ".join(words[:2])+" technology" if words else "digital technology"
def commons_cc0(item):
    """Only accept explicit reusable licenses; preserve author/license details."""
    args={"action":"query","generator":"search",
      "gsrsearch":terms(item)+" filetype:bitmap","gsrnamespace":"6",
      "gsrlimit":"30","prop":"imageinfo","iiprop":"url|extmetadata|size",
      "iiurlwidth":"1500","format":"json","formatversion":"2"}
    url=API+"?"+urllib.parse.urlencode(args)
    data=json.loads(request(url,1_000_000).decode("utf-8"))
    candidates=data.get("query",{}).get("pages",[])
    for page in candidates:
        infos=page.get("imageinfo") or []
        if not infos:continue
        meta=infos[0]
        ext=meta.get("extmetadata") or {}
        licence=html.unescape(re.sub("<[^>]*>","",str(ext.get("LicenseShortName",{}).get("value","")))).strip().lower()
        licenceurl=str(ext.get("LicenseUrl",{}).get("value","")).lower()
        # CC BY is legally reusable for a modified editorial cover provided
        # that the article displays author, license, source and modifications.
        pd=licence in ("public domain","pd","cc0","cc0 1.0","cc0 1.0 universal") or (
            "creativecommons.org/publicdomain/zero/1.0" in licenceurl
            or "creativecommons.org/publicdomain/mark/1.0" in licenceurl)
        by=(re.fullmatch(r"cc by (?:2\.0|2\.5|3\.0|4\.0)",licence) is not None
            and re.fullmatch(r"https?://creativecommons\.org/licenses/by/(?:2\.0|2\.5|3\.0|4\.0)/?",licenceurl) is not None)
        bysa=(licence.startswith("cc by-sa ") and "/licenses/by-sa/" in licenceurl)
        if not (pd or by or bysa):continue
        if int(meta.get("width") or 0)<1000 or int(meta.get("height") or 0)<650:continue
        img_url=meta.get("thumburl") or meta.get("url") or ""
        if not img_url.startswith("https://"):continue
        if not any(img_url.lower().split("?")[0].endswith(x) for x in (".jpg",".jpeg",".png",".webp")):
            # Commons resized jpg/png thumbnails can end in a hash suffix.
            if not any(x in img_url.lower() for x in (".jpg",".jpeg",".png",".webp")):continue
        try:
            raw=request(img_url,7_000_000)
            photo=Image.open(io.BytesIO(raw))
            photo.verify()
            photo=Image.open(io.BytesIO(raw)).convert("RGB")
            if photo.width<1000 or photo.height<650:continue
            return photo,{
                "origin":"Wikimedia Commons","license":("Public domain / CC0" if pd else licence.upper()),
                "source_page":meta.get("descriptionurl",""),
                "file":page.get("title",""),
                "photographer":re.sub("<[^>]*>","",str(ext.get("Artist",{}).get("value","")))[:200],
                "license_url":(licenceurl if (licenceurl.startswith("https://") or licenceurl.startswith("http://")) else "https://creativecommons.org/publicdomain/zero/1.0/"),
                "modified":True,
            }
        except (OSError,ValueError,TypeError):
            continue
    return None,None

def rgb(code):return tuple(int(code[i:i+2],16) for i in (1,3,5))
def font(size,bold=True):
    path="/usr/share/fonts/truetype/dejavu/DejaVuSans"+("-Bold" if bold else "")+".ttf"
    try:return ImageFont.truetype(path,size)
    except OSError:return ImageFont.load_default()
def cover_text(item):
    explicit=item.get("cover_headline")
    if isinstance(explicit,str) and 8<=len(explicit)<=60:return explicit.strip().upper()
    title=re.split(r"[:|–—]",item["title"])[0].strip()
    words=title.split()
    if len(words)>7:title=" ".join(words[:7])
    return title.upper()[:65]
def break_lines(draw,text,f,width,max_lines=3):
    words=text.split()
    lines=[];current=""
    for word in words:
        test=(current+" "+word).strip()
        if draw.textbbox((0,0),test,font=f)[2]<=width:
            current=test
        else:
            if current:lines.append(current)
            current=word
    if current:lines.append(current)
    return lines if len(lines)<=max_lines else None

def render(item,photo=None):
    digest=hashlib.sha256((item["section"]+"/"+item["slug"]).encode()).hexdigest()
    seed=int(digest[:10],16)
    rng=random.Random(seed)
    title=item["title"].lower()
    severity=any(x in title for x in ("attacc","violazion","fbi","risch","cyber","privacy"))
    palette_index=(seed % len(PALETTES))
    if severity:palette_index=(0,6,4)[seed%3]
    a,b=PALETTES[palette_index]
    accent=rgb(a);base=rgb(b)
    canvas=Image.new("RGB",SIZE,base)
    if photo is not None:
        canvas=ImageOps.fit(photo,SIZE,method=Image.Resampling.LANCZOS,centering=(.57,.5))
        curtain=Image.new("RGBA",SIZE,(0,0,0,0));d=ImageDraw.Draw(curtain)
        for x in range(SIZE[0]):
            alpha=int(215*(1-x/SIZE[0])**1.35+65)
            d.line((x,0,x,SIZE[1]),fill=(6,11,19,min(246,alpha)))
        canvas=Image.alpha_composite(canvas.convert("RGBA"),curtain).convert("RGB")
    else:
        d=ImageDraw.Draw(canvas)
        # Original, varied subject-specific editorial graphic (not a copied cover).
        for i in range(20):
            x=rng.randint(440,1330);y=rng.randint(-160,790);rad=rng.randint(45,260)
            colour=tuple(min(255,int(base[j]*(.5+rng.random()*.6)+accent[j]*rng.random()*.33)) for j in range(3))
            d.ellipse((x-rad,y-rad,x+rad,y+rad),outline=colour,width=rng.randint(3,18))
        for i in range(11):
            x=rng.randint(590,1280);y=rng.randint(40,680);w=rng.randint(25,180)
            d.rounded_rectangle((x,y,x+w,y+rng.randint(8,50)),radius=9,outline=accent,width=2)
        # Large icon based on the article subject.
        cx=1010;cy=350
        icon=(terms(item)+" "+item["section"]).lower()
        if "game" in icon or "controller" in icon:
            d.rounded_rectangle((820,295,1190,458),radius=75,outline=(237,242,247),width=23)
            d.line((883,368,966,368),fill=accent,width=18)
            d.line((925,327,925,410),fill=accent,width=18)
            d.ellipse((1080,330,1107,357),fill=accent)
            d.ellipse((1120,375,1147,402),fill=accent)
        elif "glasses" in icon:
            d.rounded_rectangle((818,300,979,415),radius=34,outline=(243,245,250),width=18)
            d.rounded_rectangle((1032,300,1193,415),radius=34,outline=(243,245,250),width=18)
            d.line((979,345,1032,345),fill=accent,width=17)
        else:
            vertices=[(cx,198),(1140,262),(1124,441),(cx,545),(896,441),(880,262)]
            d.polygon(vertices,outline=(234,245,253),width=16)
            d.ellipse((966,326,1054,409),outline=accent,width=18)
    d=ImageDraw.Draw(canvas)
    d.rectangle((0,0,1280,9),fill=accent)
    d.rounded_rectangle((48,48,280,94),radius=12,fill=(13,20,28))
    d.text((63,57),"ZazoomTek.it",font=font(28),fill=(255,255,255))
    d.text((52,126),"TECH IMPACT" if item["section"]=="tech" else "GAMING INSIDE",
            font=font(23),fill=accent,stroke_width=0)
    headline=cover_text(item)
    f=None;lines=None
    for size in range(66,37,-2):
        candidate=font(size)
        part=break_lines(d,headline,candidate,740,3)
        if part is not None:
            f=candidate;lines=part;break
    if lines is None:
        f=font(38);lines=break_lines(d,headline[:35],f,740,3) or [headline[:35]]
    line_height=d.textbbox((0,0),"Ag",font=f)[3]+26
    start_y=max(230,370-line_height*len(lines)//2)
    for i,line in enumerate(lines):
        d.text((51,start_y+i*line_height),line,font=f,fill=(255,255,255),
             stroke_width=2,stroke_fill=(8,14,25))
    bar_y=min(610,start_y+len(lines)*line_height+12)
    d.rectangle((52,bar_y,505,bar_y+8),fill=accent)
    summary=item.get("cover_subtitle") or item.get("summary","")
    if len(summary)>88:summary=summary[:85].rsplit(" ",1)[0]+"…"
    small=font(21,False)
    for j,part in enumerate(break_lines(d,summary,small,800,3) or [summary[:65]]):
        d.text((54,min(655,bar_y+30+j*29)),part,font=small,fill=(245,245,245),
               stroke_width=1,stroke_fill=(0,0,0))
    return canvas

def encode(img):
    buf=io.BytesIO()
    for quality in (83,78,72,66,59,52,45,38):
        buf.seek(0);buf.truncate()
        img.save(buf,"WEBP",quality=quality,method=6)
        if buf.tell()<=MAX_BYTES:return buf.getvalue()
    raise ValueError("Unable to optimize cover below 300 KB")

def main():
    docs=json.loads(APPROVED.read_text(encoding="utf-8"))
    entries=docs.get("articles",[])
    old=json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"articles":{}}
    manifest=old.get("articles",{})
    changed=False
    for item in entries:
        if not isinstance(item,dict) or not item.get("editor_approved"):continue
        if item.get("section") not in ("tech","gaming"):continue
        slug=item.get("slug","")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",slug):continue
        # Only replace editorial covers explicitly marked 'auto'. Otherwise
        # respect any existing image chosen by the editor.
        automatic=item.get("cover_mode")=="auto"
        if item.get("image") and item["image"]!="/ChatGPT.png" and not automatic:continue
        key=item["section"]+"/"+slug
        relative="assets/special/"+shortname(item)+".webp"
        target=ROOT/relative
        if target.is_file() and target.stat().st_size<=MAX_BYTES:
            if manifest.get(key,{}).get("path")=="/"+relative:continue
        try:
            photo,rights=commons_cc0(item)
        except Exception as exc:
            photo,rights=None,None
            print("Commons unavailable; using original artwork:",str(exc)[:130])
        encoded=encode(render(item,photo))
        if not target.exists() or target.read_bytes()!=encoded:
            target.write_bytes(encoded);changed=True
        manifest[key]={
          "path":"/"+relative,
          "origin":rights or {"origin":"ZazoomTek original graphic","license":"Original in-house art"},
          "search_terms":terms(item),
          "bytes":len(encoded),
        }
        changed=True
        print("Cover ready:",relative,len(encoded),"bytes",rights["origin"] if rights else "original")
    content=json.dumps({"articles":manifest},ensure_ascii=False,indent=2)+"\n"
    if not OUT.exists() or OUT.read_text(encoding="utf-8")!=content:
        OUT.write_text(content,encoding="utf-8");changed=True
    print("Cover pipeline finished; changed:",changed)
def self_test():
    """Exercise the rights-safe fallback, typography and WebP compression."""
    item={
      "section":"tech","slug":"test-sicurezza-infrastrutture",
      "title":"La sicurezza delle infrastrutture digitali in Europa",
      "summary":"Un controllo locale della generazione di copertine originali senza servizi esterni.",
    }
    raw=encode(render(item))
    assert 0<len(raw)<=MAX_BYTES,(len(raw),MAX_BYTES)
    picture=Image.open(io.BytesIO(raw))
    assert picture.format=="WEBP" and picture.size==SIZE,(picture.format,picture.size)
    assert terms(item), "Cover search terms are empty"
    print("COVER SELF TEST PASSED:",len(raw),"bytes",picture.size)

if __name__=="__main__":
    import sys
    self_test() if "--self-test" in sys.argv else main()
