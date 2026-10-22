#!/usr/bin/env python3
"""Use only real ZazoomTek editorial pages for the new right rail and EXTRA.
This module is presentation only; it doesn't import or publish anything.
"""
from __future__ import annotations
from html import escape, unescape
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
EXTRA_START="<!-- ZT_WEB_EXTRA_START -->"
EXTRA_END="<!-- ZT_WEB_EXTRA_END -->"
RAIL_START="<!-- ZT_WEB_EDITORIAL_RAIL_START -->"
RAIL_END="<!-- ZT_WEB_EDITORIAL_RAIL_END -->"

def metadata(page:Path):
    content=page.read_text(encoding="utf-8",errors="replace")
    h1=re.search(r"<h1\b[^>]*>([\s\S]*?)</h1>",content,re.I)
    t=re.search(r"<title\b[^>]*>([\s\S]*?)</title>",content,re.I)
    raw=h1.group(1) if h1 else t.group(1) if t else page.stem.replace("-"," ")
    title=unescape(re.sub(r"<[^>]*>","",raw)).strip()
    title=re.sub(r"\s+"," ",title).replace(" | ZazoomTek","").replace(" - ZazoomTek","")
    if not title:raise ValueError("No title "+page.name)
    published=""
    for m in re.finditer(r"<meta\b[^>]*>",content,re.I):
        tag=m.group()
        if "article:published_time" in tag.lower():
            n=re.search(r'\bcontent\s*=\s*["\']([^"\']+)',tag,re.I)
            if n:published=n.group(1);break
    if not published:
        stamp=re.search(r'"datePublished"\s*:\s*"([^"]+)"',content)
        if stamp:published=stamp.group(1)
    img=""
    paths=re.findall(r'\bsrc\s*=\s*["\'](/assets/(?:special|recensioni|guides)/[^"\']+)',content,re.I)
    for candidate in paths:
        if ".." in candidate or not candidate.endswith((".jpg",".png",".jpeg",".webp",".svg")):continue
        if (page.parent/candidate.lstrip("/")).is_file():
            img=candidate;break
    if not img:
        # Own site's logo is safer than attributing a wrong editorial photograph.
        img="/assets/zt-header-logo-128.png"
    return {"title":title,"image":img,"href":"/"+page.name,"date":published,"stem":page.stem}

def collect(root=ROOT):
    specs=(
        ("Da non perdere","/cybercultura.html","tech-impact-*.html",3),
        ("Dalla redazione","/cybercultura.html","gaming-inside-*.html",3),
        ("Recensioni Tech","/recensioni-scritte.html","*recensione*.html",3),
    )
    boxes=[]
    for heading,target,pattern,limit in specs:
        docs=[]
        for path in root.glob(pattern):
            if path.name.startswith(("preview","anteprima","recensioni-","news-")):continue
            try:d=metadata(path)
            except (OSError,ValueError):continue
            if heading=="Recensioni Tech" and not any(
                term in path.name for term in ("70mai","thermomate","iifactor","realme","reolink","geekom","keychron","dashcam")
            ):continue
            docs.append(d)
        docs.sort(key=lambda x:(x["date"],x["stem"]),reverse=True)
        boxes.append((heading,target,docs[:limit]))
    return boxes

def render_rail(root=ROOT):
    blocks=[]
    for title,archive,items in collect(root):
        if not items:continue
        cards=[]
        for item in items:
            cards.append(
                '<a class="zt-webnews-rail-card" href="'+escape(item["href"],quote=True)+'">'
                '<img src="'+escape(item["image"],quote=True)+'" alt="" width="112" height="74" loading="lazy" decoding="async">'
                '<strong>'+escape(item["title"])+'</strong></a>'
            )
        blocks.append(
            '<section class="zt-webnews-rail-box">'
            '<header><h3>'+escape(title)+'</h3><a href="'+escape(archive,quote=True)+'">TUTTE →</a></header>'
            '<div class="zt-webnews-rail-cards">'+"".join(cards)+'</div></section>'
        )
    if not blocks:raise ValueError("No existing ZazoomTek articles available for the right editorial rail")
    return RAIL_START+'<aside class="zt-webnews-followup-rail" aria-label="Box editoriali ZazoomTek">'+''.join(blocks)+'</aside>'+RAIL_END

def render_extra(root=ROOT):
    docs=[]
    for path in root.glob("extra-*.html"):
        try:docs.append(metadata(path))
        except (OSError,ValueError):continue
    docs.sort(key=lambda x:(x["date"],x["stem"]),reverse=True)
    if not docs:return ""
    cards=''.join('<a class="zt-webnews-extra-card" href="'+escape(i["href"],quote=True)+'"><span>EXTRA</span><strong>'+escape(i["title"])+'</strong><small>Leggi su ZazoomTek →</small></a>' for i in docs[:2])
    return EXTRA_START+'<section class="zt-webnews-extra" id="ztWebNewsExtra" aria-label="Articoli Extra"><header><h2>EXTRA</h2><a href="/extra.html">VEDI TUTTO →</a></header><div class="zt-webnews-extra-grid">'+cards+'</div></section>'+EXTRA_END

CSS=r"""
/* Full-width aligned bottom Home row; existing top/three-column layout untouched. */
.zt-webnews-followup{display:grid;grid-template-columns:minmax(0,1fr) clamp(370px,31vw,420px);gap:24px;align-items:start;width:100%;clear:both;margin:18px 0 28px}
.zt-webnews-followup-main{min-width:0}
.zt-webnews-followup .zt-webnews{margin:0 0 17px}
.zt-webnews-followup #ztHomeGuide{margin:0 0 17px;max-width:none}
.zt-webnews-followup-rail{display:flex;flex-direction:column;gap:16px;min-width:0}
.zt-webnews-rail-box{background:white;border:1px solid #e3e3e3;min-width:0}
.zt-webnews-rail-box header,.zt-webnews-extra header{background:#1c1c1e;color:white;min-height:44px;display:flex;justify-content:space-between;align-items:center;gap:8px;padding:0 13px}
.zt-webnews-rail-box header h3,.zt-webnews-extra h2{margin:0;font:900 13px/1.3 Arial,sans-serif;letter-spacing:.02em;text-transform:uppercase}
.zt-webnews-rail-box header a,.zt-webnews-extra header a{font:800 10px/1.3 Arial,sans-serif;color:#fff;text-decoration:none;white-space:nowrap}
.zt-webnews-rail-card{padding:10px;display:grid;grid-template-columns:112px minmax(0,1fr);gap:11px;align-items:center;border-bottom:1px solid #ededed;min-height:91px;color:#18191d;text-decoration:none}
.zt-webnews-rail-card:last-child{border-bottom:0}
.zt-webnews-rail-card:hover strong{color:#d51232}
.zt-webnews-rail-card img{width:112px;height:74px;object-fit:cover;border-radius:2px;background:#f0f0f1}
.zt-webnews-rail-card strong{font:800 13px/1.33 Arial,sans-serif;overflow-wrap:anywhere;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:3;overflow:hidden}
.zt-webnews-extra{background:#fff;border:1px solid #e1e1e1;margin:0 0 16px;min-width:0}
.zt-webnews-extra-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;padding:14px}
.zt-webnews-extra-card{border:1px solid #ececef;border-radius:3px;background:#fbfbfc;text-decoration:none;color:#1c1e22;display:flex;flex-direction:column;gap:8px;justify-content:space-between;min-height:150px;padding:16px}
.zt-webnews-extra-card span{font:850 10px Arial,sans-serif;color:#d51232;letter-spacing:.07em}
.zt-webnews-extra-card strong{font:850 15px/1.32 Arial,sans-serif}
.zt-webnews-extra-card small{font:750 11px/1.3 Arial,sans-serif;color:#747781}
.zt-webnews-extra-card:hover strong{color:#bd1234}
@media(max-width:1100px){.zt-webnews-followup{grid-template-columns:minmax(0,1fr) 300px;gap:14px}.zt-webnews-rail-card{grid-template-columns:95px minmax(0,1fr)}.zt-webnews-rail-card img{width:95px;height:67px}}
@media(max-width:850px){.zt-webnews-followup{grid-template-columns:1fr}.zt-webnews-followup-rail{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:560px){.zt-webnews-followup-rail{grid-template-columns:1fr}.zt-webnews-extra-grid{grid-template-columns:1fr}}
"""
