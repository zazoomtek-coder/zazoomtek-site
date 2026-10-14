#!/usr/bin/env python3
"""Create 1200x675 letterboxed editorial sharing assets for small remote covers.

Original article images remain unchanged. Never fabricate image detail or rewrite
editorial content. Only canonical article OpenGraph/Twitter image heads change.
"""
import argparse
import hashlib
import html
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit
from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError
from seo_paths_safe import html_pages, canonical_candidates
from seo_head_safe import Metadata
from seo_discover_readiness import Head, END_HEAD

BASE="https://zazoomtek.it"
ROOTNAME="assets/discover/community"
SIZE=(1200,675)
MAX_READ=8*1024*1024
OG=re.compile(r'<meta\b[^>]*property=["\x27]og:image["\x27][^>]*>',re.I)
TW=re.compile(r'<meta\b[^>]*name=["\x27]twitter:image["\x27][^>]*>',re.I)

def fetch(url):
    try:
        request=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 ZazoomTekDiscoverCard"})
        with urllib.request.urlopen(request,timeout=9) as response:
            if response.status!=200:return None
            blob=response.read(MAX_READ+1)
            if len(blob)>MAX_READ:return None
        with Image.open(BytesIO(blob)) as im:
            im.load()
            # Keep high-resolution covers local too, avoiding remote availability issues.
            if im.width<120 or im.height<120:return None
            return im.convert("RGB")
    except (OSError,ValueError,UnidentifiedImageError):
        return None

def pages(root):
    matches={}
    for page in html_pages(root):
        if re.fullmatch(r"news-\d+\.html",page.name):continue
        raw=page.read_text(encoding="utf-8",errors="replace")
        m=END_HEAD.search(raw)
        if not m:continue
        head=raw[:m.start()]
        meta=Metadata();meta.feed(head)
        if len(meta.canonicals)!=1 or meta.canonicals[0] not in canonical_candidates(root,page):continue
        if "noindex" in " ".join(meta.meta.get(k,"") for k in ("robots","googlebot")).lower():continue
        if not (meta.meta.get("og:type","").lower()=="article" or page.name.startswith(("news-","recensione-","tech-impact-","gaming-inside-","guida-")) or "recensione" in page.name):continue
        p=Head();p.feed(head)
        if len(p.image)!=1:continue
        url=p.image[0]
        if urlsplit(url).scheme!="https" or urlsplit(url).netloc in ("zazoomtek.it","www.zazoomtek.it"):continue
        matches.setdefault(url,[]).append(page)
    return matches

def fallback_card(root,url,page):
    source=page.read_text(encoding="utf-8",errors="replace")
    match=re.search(r"<title[^>]*>(.*?)</title>",source,re.I|re.S)
    title=html.unescape(re.sub(r"<[^>]+>"," ",match.group(1))) if match else page.stem
    title=re.sub(r"\\s*\\|\\s*ZazoomTek\\s*$","",title,flags=re.I).strip()
    name=hashlib.sha256(url.encode("utf-8")).hexdigest()[:22]+"-editorial.webp"
    output=root/ROOTNAME/name
    output.parent.mkdir(parents=True,exist_ok=True)
    img=Image.new("RGB",SIZE,(24,29,42))
    draw=ImageDraw.Draw(img)
    draw.rectangle((0,0,15,675),fill=(214,18,50))
    font_path="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    face=ImageFont.truetype(font_path,48) if Path(font_path).exists() else ImageFont.load_default()
    draw.text((66,80),"ZAZOOMTEK  |  COMMUNITY",font=face,fill=(255,108,127))
    words=title.split();rows=[];line=""
    for word in words:
        candidate=(line+" "+word).strip()
        if draw.textbbox((0,0),candidate,font=face)[2]>1030 and line:
            rows.append(line);line=word
        else:line=candidate
    if line:rows.append(line)
    for i,row in enumerate(rows[:5]):
        draw.text((66,185+i*82),row,font=face,fill="white")
    img.save(output,format="WEBP",quality=88,method=5)
    return BASE+"/"+ROOTNAME+"/"+name

def save_card(root,url,picture):
    stem=hashlib.sha256(url.encode("utf-8")).hexdigest()[:22]+".webp"
    output=root/ROOTNAME/stem
    output.parent.mkdir(parents=True,exist_ok=True)
    if not output.exists():
        image=Image.new("RGB",SIZE,(23,28,40))
        visual=ImageOps.contain(picture,(1160,620),Image.Resampling.LANCZOS)
        x=(SIZE[0]-visual.width)//2
        y=(SIZE[1]-visual.height)//2
        image.paste(visual,(x,y))
        draw=ImageDraw.Draw(image)
        draw.rectangle((0,0,12,675),fill=(215,19,50))
        image.save(output,format="WEBP",quality=85,method=5)
    with Image.open(output) as im:
        if im.size!=SIZE:raise RuntimeError("Bad generated dimensions")
    return BASE+"/"+ROOTNAME+"/"+stem

def update(page,old,new):
    source=page.read_text(encoding="utf-8")
    m=END_HEAD.search(source)
    if not m:return False
    head,tail=source[:m.start()],source[m.start():]
    tags=OG.findall(head)
    if len(tags)!=1:return False
    head=head.replace(tags[0],'<meta property="og:image" content="'+html.escape(new,quote=True)+'">',1)
    twitter=TW.findall(head)
    if len(twitter)==1:
        head=head.replace(twitter[0],'<meta name="twitter:image" content="'+html.escape(new,quote=True)+'">',1)
    elif not twitter:head+='\n<meta name="twitter:image" content="'+html.escape(new,quote=True)+'">'
    # Replace same matching cover in existing Article schema without touching
    # article text or unrelated image references in the page.
    head=head.replace('"image":"'+old+'"','"image":"'+new+'"')
    head=head.replace('"image":["'+old+'"]','"image":["'+new+'"]')
    out=head+tail
    assert out.endswith(tail)
    if out!=source:page.write_text(out,encoding="utf-8")
    return True

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--root",type=Path,default=Path("."))
    args=parser.parse_args();root=args.root.resolve()
    targets=pages(root)
    count=0;unavailable=0;revised=0
    with ThreadPoolExecutor(max_workers=12) as pool:
        jobs={pool.submit(fetch,url):url for url in targets}
        for job in as_completed(jobs):
            url=jobs[job]
            image=job.result()
            if image is None:
                unavailable+=1
                card=fallback_card(root,url,targets[url][0])
            else:
                card=save_card(root,url,image)
                count+=1
            for page in targets[url]:
                revised+=int(update(page,url,card))
    # Final safeguard: no third-party image may remain in an editorial
    # sharing preview, even if its source failed an earlier download.
    remaining=pages(root)
    final_fixed=0
    for url,files in remaining.items():
        card=fallback_card(root,url,files[0])
        for page in files:
            final_fixed+=int(update(page,url,card))
    print(f"Discover sharing cards: {count} source-image cards; {revised} pages updated; {unavailable} fallback sources; {final_fixed} residual metadata corrections")

if __name__=="__main__":main()
