#!/usr/bin/env python3
"""Independent Home and Community page publisher for ZazoomTek.

Never resets the canonical Home structure. Keeps all previously published
articles; new Community posts get standalone HTML, archive and Home cards.
The existing CSS and visual templates are retained unchanged.
"""
from __future__ import annotations
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"services10-data"
HOME_START="<!-- SERVICES10_COMMUNITY_HOME_START -->"
HOME_END="<!-- SERVICES10_COMMUNITY_HOME_END -->"
ARCH_START="<!-- SERVICES10_COMMUNITY_ARCHIVE_START -->"
ARCH_END="<!-- SERVICES10_COMMUNITY_ARCHIVE_END -->"

def load_list(path:Path)->list[dict]:
    try:
        data=json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data,list) else []
    except (ValueError,OSError):
        return []

def title_of(post:dict)->str:
    raw=str(post.get("text") or post.get("title") or "").strip()
    line=next((line.strip() for line in raw.splitlines() if line.strip()),"")
    line=re.sub(r"^\s*(?:🇮🇹|🇬🇧|📰)\s*","",line)
    line=re.sub(r"^\*+|\*+$","",line).strip()
    line=re.sub(r"(?i)^news\s*:\s*","",line)
    return line[:180] or str(post.get("title") or "")[:180]

def classify(post:dict)->str:
    label=str(post.get("text") or post.get("title") or "")[:280].lower()
    if re.search(r"(?i)(?:news\s+(?:gaming|videogiochi)|\b(?:playstation|xbox|nintendo|ps5|steam|gameplay|videogioch[io])\b)",label):
        return "gaming"
    if re.search(r"(?i)(?:news\s+(?:tech|tecnologia)|\b(?:smartphone|robot|fotocamer|notebook|laptop|processore|intel|nvidia|amd|wi-fi|televisor|smartwatch|apple|samsung)\b)",label):
        return "tech"
    return "news"

def items(root:Path=ROOT)->list[dict]:
    found=[];seen=set()
    for post in load_list(root/"services10-data"/"community.json"):
        if not isinstance(post,dict):continue
        ident=str(post.get("id") or "")
        if not re.fullmatch(r"Ugkx[A-Za-z0-9_-]{5,100}",ident) or ident in seen:
            continue
        seen.add(ident)
        body=str(post.get("text") or "").strip()
        if not body:continue
        found.append({"id":ident,"url":"/news-"+ident+".html",
                      "title":title_of(post),"text":body,
                      "section":classify(post),
                      "image":str(post.get("image") or ""),
                      "first_seen":str(post.get("first_seen") or "")})
    return found

def article_content(text:str)->str:
    paragraphs=[]
    for part in re.split(r"\n\s*\n",text.strip()):
        lines=part.splitlines()
        cleaned="<br>".join(html.escape(line.strip()) for line in lines if line.strip())
        if cleaned:paragraphs.append("<p>"+cleaned+"</p>")
    return "\n".join(paragraphs)

def replace_owned(source:str,start:str,end:str,new:str)->str:
    owned=start+"\n"+new+"\n"+end
    if start in source and end in source:
        before=source.index(start)
        after=source.index(end,before)+len(end)
        return source[:before]+owned+source[after:]
    return source

def render_detail(item:dict)->str:
    title=html.escape(item["title"])
    description=html.escape(item["text"][:155].replace("\n"," "),quote=True)
    category=html.escape(item["section"].upper())
    content=article_content(item["text"])
    url="https://zazoomtek.it"+item["url"]
    cover=('<img class="article-hero" src="'+html.escape(item["image"],quote=True)+
           '" alt="'+title+'" loading="eager">' if item["image"] else "")
    return f'''<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | ZazoomTek</title><meta name="description" content="{description}">
<meta name="robots" content="index,follow,max-image-preview:large">
<link rel="canonical" href="{html.escape(url,quote=True)}">
<meta property="og:type" content="article"><meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{html.escape(url,quote=True)}">
<link rel="icon" href="/ChatGPT.png"><link rel="stylesheet" href="/zt-design.css">
<style>body{{margin:0;font-family:Arial,Helvetica,sans-serif;background:#efefef;color:#202020}}
.zt-wrap{{width:min(1200px,calc(100% - 28px));margin:auto}}
.zt-header{{background:#191919;border-top:3px solid #d51232;color:white;padding:20px 0}}
.zt-brand{{font-size:25px;color:white;font-weight:900;text-decoration:none}}
.zt-nav{{display:flex;gap:22px;flex-wrap:wrap;padding-top:11px}}
.zt-nav a{{color:white;text-decoration:none;font-weight:700;font-size:13px}}
.news-detail-page{{padding:26px 0 55px}}
.article-main{{background:white;padding:clamp(16px,4vw,44px);max-width:900px;margin:auto}}
.article-main h1{{font-size:clamp(29px,4vw,44px);line-height:1.12}}
.article-meta{{color:#777;margin:18px 0}}
.article-body{{font-size:17px;line-height:1.7;overflow-wrap:anywhere}}
.article-body p{{margin:0 0 18px;white-space:normal}}
.article-hero{{width:100%;aspect-ratio:16/9;object-fit:cover}}
.zt-content-footer{{background:#191919;color:white;padding:24px;text-align:center}}
.zt-content-footer a{{color:white}}
</style></head><body>
<header class="zt-header"><div class="zt-wrap"><a class="zt-brand" href="/">ZazoomTek</a>
<nav class="zt-nav"><a href="/">HOME</a><a href="/news.html">NEWS</a>
<a href="/recensioni-scritte.html">RECENSIONI</a><a href="/guide.html">GUIDE</a>
<a href="/speciali.html">SPECIALI</a></nav></div></header>
<main class="news-detail-page"><div class="zt-wrap"><article class="article-main">
<div class="breadcrumbs"><a href="/">Home</a> / <a href="/news.html">News</a> / {category}</div>
<h1>{title}</h1><div class="article-meta">ZazoomTek · {category}</div>
{cover}<div class="article-body">{content}</div>
<p><a href="/news.html">← Torna alle news</a></p></article></div></main>
<footer class="zt-content-footer"><a href="/">ZazoomTek.it</a> · Tech · Gaming</footer>
<script src="/studio/edit-button.js" defer></script></body></html>'''

def render_home_card(item:dict)->str:
    title=html.escape(item["title"],quote=True)
    href=html.escape(item["url"],quote=True)
    picture=('<a href="'+href+'"><img class="article-image" src="'+
             html.escape(item["image"],quote=True)+'" alt="'+title+
             '" loading="lazy"></a>' if item["image"] else "")
    summary=html.escape(re.sub(r"\s+"," ",item["text"])[:200])
    return ('<article class="article-row" data-post-category="'+item["section"]+
       '" data-published-at="'+html.escape(item["first_seen"],quote=True)+'">'+picture+
       '<div class="article-copy"><h3><a href="'+href+'">'+title+
       '</a></h3><div class="article-meta">ZazoomTek · Community</div><p>'+summary+
       '…</p><a class="read-more" href="'+href+'">Leggi tutto ›</a></div></article>')

def render_archive_card(item:dict)->str:
    title=html.escape(item["title"],quote=True)
    href=html.escape(item["url"],quote=True)
    picture=('<a href="'+href+'"><img src="'+html.escape(item["image"],quote=True)+
             '" alt="'+title+'" loading="lazy"></a>' if item["image"] else "")
    return ('<article class="news-row" data-post-category="'+item["section"]+
       '" data-published-at="'+html.escape(item["first_seen"],quote=True)+'">'+
       picture+'<div class="news-copy"><h2><a href="'+href+'">'+title+
       '</a></h2><div class="news-meta">ZazoomTek · Community</div></div></article>')

def update(root:Path=ROOT)->dict:
    publications=items(root)
    if not publications:return {"posts":0,"created_pages":0}
    created=0
    for post in publications:
        target=root/post["url"].lstrip("/")
        if not target.exists():
            target.write_text(render_detail(post),encoding="utf-8")
            created+=1
    news=root/"news.html"
    if news.is_file():
        document=news.read_text(encoding="utf-8")
        cards="\n".join(render_archive_card(p) for p in publications if
                        "href=\""+p["url"]+"\"" not in document)
        if cards:
            if ARCH_START in document and ARCH_END in document:
                updated=replace_owned(document,ARCH_START,ARCH_END,cards)
            else:
                updated=re.sub(r'<article class="news-row"',ARCH_START+"\n"+cards+"\n"+ARCH_END+
                               '\n<article class="news-row"',document,count=1)
            if updated!=document:news.write_text(updated,encoding="utf-8")
    home=root/"index.html"
    if home.is_file():
        document=home.read_text(encoding="utf-8")
        cards="\n".join(render_home_card(p) for p in publications[:12] if
                        "href=\""+p["url"]+"\"" not in document)
        if cards:
            if HOME_START in document and HOME_END in document:
                updated=replace_owned(document,HOME_START,HOME_END,cards)
            else:
                updated=document.replace("<!-- ARTICLE_FEED_START -->",
                  "<!-- ARTICLE_FEED_START -->\n"+HOME_START+"\n"+cards+"\n"+
                  HOME_END,1)
            if updated!=document:home.write_text(updated,encoding="utf-8")
    print("Community: archived",len(publications),"new pages",created)
    return {"posts":len(publications),"created_pages":created}

if __name__=="__main__":
    update()
