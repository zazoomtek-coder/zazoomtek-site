#!/usr/bin/env python3
"""Independent WRITTEN Community and News publisher for ZazoomTek.

Does not import, alter or classify YouTube videos. Keeps all previously published
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

def original_title(text:str)->str:
    lines=[re.sub(r"^\s*(?:🇮🇹|🇬🇧|📰)\s*","",l).strip(" *\t")
           for l in str(text or "").splitlines()]
    lines=[l for l in lines if l]
    if not lines:return "News ZazoomTek"
    first=lines[0]
    first=re.sub(r"(?i)^(?:(?:news\s+)?(?:tech|game|gaming|speciale|speciali|extra|recensioni|review|reviews)\s*:\s*|news\s*:\s*)","",first).strip()
    if not first and len(lines)>1:first=lines[1]
    return first[:180] or "News ZazoomTek"

def title_of(post:dict)->str:
    return original_title(post.get("text") or post.get("title") or "")

def classify(post:dict)->str:
    """Stable editorial routing: preserve every real YouTube Community category."""
    body=str(post.get("text") or post.get("title") or "")
    heading=next((line.strip().lstrip("🇮🇹 ").strip()
                  for line in body.splitlines() if line.strip()),"")
    route=re.match(r"(?i)^(?:news\s+)?(tech|game|gaming|speciale|speciali|extra|recensioni|review|reviews)\s*:",heading)
    if route:
        value=route.group(1).lower()
        return {"game":"gaming","speciale":"speciali","recensioni":"reviews",
                "review":"reviews"}.get(value,value)
    if re.match(r"(?i)^news\s*:\s*",heading):
        return "news"
    label=heading[:280].lower()
    if re.search(r"\b(recensione|review)\b",label):return "reviews"
    if re.search(r"\b(playstation|xbox|nintendo|ps5|steam|gameplay|videogioch[io])\b",label):
        return "gaming"
    if re.search(r"\b(smartphone|robot|notebook|laptop|intel|nvidia|amd|wi-fi|televisor|smartwatch|apple|samsung)\b",label):
        return "tech"
    return "news"

SOCIAL_LINE=re.compile(
    r"(?i)^\s*(?:subscribe\b|iscriviti\b|"
    r"(?:🌐\s*)?zazoomtek\.it\b|(?:▶️\s*)?youtube\s*:|"
    r"(?:❤️\s*)?patreon\s*:|(?:🎵\s*)?tiktok\s*:|"
    r"(?:💬\s*)?whatsapp\s*:|#\S+)"
)
def site_blocks(raw:str,title:str="")->list[str]:
    """Preserve authored sections while omitting Community-only footer."""
    lines=[]
    for segment in re.split(r"\n\s*\n|⠀",str(raw or "")):
        for line in segment.splitlines():
            line=line.strip()
            if not line or SOCIAL_LINE.match(line):continue
            if line==title or original_title(line)==title and len(lines)==0:
                continue
            lines.append(line)
    return lines

def article_content(text:str,title:str="",images:list[str]|None=None)->str:
    blocks=site_blocks(text,title)
    markup=[]
    for line in blocks:
        markup.append("<p>"+html.escape(line)+"</p>")
    # If YouTube supplied multiple photos, keep the main cover above and
    # insert additional gallery pictures between the authored paragraphs.
    photos=[str(u) for u in (images or [])[1:] if str(u).startswith("https://")]
    if photos:
        at=max(1,len(markup)//2)
        gallery="".join('<figure class="zt-community-gallery"><img src="'+
                 html.escape(u,quote=True)+'" loading="lazy" alt="'+
                 html.escape(title,quote=True)+'"></figure>' for u in photos[:8])
        markup.insert(at,gallery)
    return "\n".join(markup)

def deduplicate_posts(posts:list[dict])->list[dict]:
    """One record per YouTube post ID. Never drop distinct posts with identical titles."""
    by_id={}
    for post in posts:
        if not isinstance(post,dict):continue
        ident=str(post.get("id") or "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{6,128}",ident):continue
        old=by_id.get(ident)
        if old is None:
            by_id[ident]=post
            continue
        better=post if len(str(post.get("text") or ""))>len(str(old.get("text") or "")) else old
        merged={**old,**{k:v for k,v in better.items() if v not in ("",None,[])}}
        # Never lose an original publication timestamp or any existing images.
        for key in ("published_iso","first_seen"):
            if old.get(key):merged[key]=old[key]
        images=list(dict.fromkeys((old.get("images") or [])+(post.get("images") or [])))
        if images:merged["images"]=images
        by_id[ident]=merged
    return sorted(by_id.values(),key=lambda p:str(p.get("published_iso") or p.get("first_seen") or ""),reverse=True)

def deduplicate_cards(cards:list[dict])->list[dict]:
    """One published article per canonical URL/title, newest first."""
    result=[];seen_urls=set();seen_titles=set()
    for item in sorted(cards,key=lambda x:str(x.get("published_iso") or x.get("first_seen") or ""),reverse=True):
        url=str(item.get("url") or "").split("?",1)[0].lower()
        title=re.sub(r"\s+"," ",str(item.get("title") or "")).casefold().strip()
        if not url or url in seen_urls:continue
        seen_urls.add(url)
        if title:seen_titles.add(title)
        result.append(item)
    return result

def items(root:Path=ROOT)->list[dict]:
    found=[]
    for post in deduplicate_posts(load_list(root/"services10-data"/"community.json")):
        if not isinstance(post,dict):continue
        ident=str(post.get("id") or "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{6,128}",ident):
            continue
        body=str(post.get("text") or "").strip()
        if not body:continue
        pictures=post.get("images") if isinstance(post.get("images"),list) else []
        found.append({"id":ident,"url":"/news-"+ident+".html",
                      "title":title_of(post),"text":body,
                      "section":classify(post),
                      "image":str(post.get("image") or (pictures[0] if pictures else "")),
                      "images":pictures,
                      "published_iso":str(post.get("published_iso") or ""),
                      "first_seen":str(post.get("first_seen") or "")})
    return deduplicate_cards(found)

def replace_owned(source:str,start:str,end:str,new:str)->str:
    owned=start+"\n"+new+"\n"+end
    if start in source and end in source:
        before=source.index(start)
        after=source.index(end,before)+len(end)
        return source[:before]+owned+source[after:]
    return source

def published_label(item:dict)->str:
    iso=str(item.get("published_iso") or item.get("first_seen") or "")
    try:
        dt=datetime.fromisoformat(iso.replace("Z","+00:00"))
        months="gennaio febbraio marzo aprile maggio giugno luglio agosto settembre ottobre novembre dicembre".split()
        return f"{dt.day} {months[dt.month-1]} {dt.year}"
    except (ValueError,TypeError):
        return ""

def render_detail(item:dict)->str:
    title=html.escape(item["title"])
    description=html.escape(" ".join(site_blocks(item["text"],item["title"]))[:155],quote=True)
    category=html.escape(item["section"].upper())
    destination={"speciali":"/speciali.html","extra":"/extra.html",
                 "reviews":"/recensioni-scritte.html"}.get(item["section"],"/news.html")
    content=article_content(item["text"],item["title"],item.get("images"))
    url="https://zazoomtek.it"+item["url"]
    published=html.escape(item.get("published_iso") or item.get("first_seen") or "",quote=True)
    human_date=html.escape(published_label(item))
    cover=('<img class="article-hero" src="'+html.escape(item["image"],quote=True)+
           '" alt="'+title+'" loading="eager">' if item["image"] else "")
    return f'''<!-- SERVICES10_GENERATED -->\n<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | ZazoomTek</title><meta name="description" content="{description}">
<meta name="robots" content="index,follow,max-image-preview:large">
<link rel="canonical" href="{html.escape(url,quote=True)}">
<meta property="og:type" content="article"><meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="article:published_time" content="{published}">
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
.zt-community-gallery{{margin:20px auto;max-width:840px}}
.zt-community-gallery img{{max-width:100%;height:auto;display:block}}
.zt-content-footer{{background:#191919;color:white;padding:24px;text-align:center}}
.zt-content-footer a{{color:white}}
</style></head><body>
<header class="zt-header"><div class="zt-wrap"><a class="zt-brand" href="/">ZazoomTek</a>
<nav class="zt-nav"><a href="/">HOME</a><a href="/news.html">NEWS</a>
<a href="/recensioni-scritte.html">RECENSIONI</a><a href="/guide.html">GUIDE</a>
<a href="/speciali.html">SPECIALI</a></nav></div></header>
<main class="news-detail-page"><div class="zt-wrap"><article class="article-main">
<div class="breadcrumbs"><a href="/">Home</a> / <a href="{destination}">{category}</a></div>
<h1>{title}</h1><div class="article-meta">ZazoomTek · {category} · <time datetime="{published}">{human_date}</time></div>
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
    summary=html.escape(" ".join(site_blocks(item["text"],item["title"]))[:200])
    label=html.escape(published_label(item))
    stamp=html.escape(item.get("published_iso") or item.get("first_seen") or "",quote=True)
    return ('<article class="article-row" data-post-category="'+item["section"]+
       '" data-published-at="'+html.escape(item.get("published_iso") or item["first_seen"],quote=True)+'">'+picture+
       '<div class="article-copy"><h3><a href="'+href+'">'+title+
       '</a></h3><div class="article-meta">ZazoomTek · <time datetime="'+stamp+'">'+label+'</time></div><p>'+summary+
       '…</p><a class="read-more" href="'+href+'">Leggi tutto ›</a></div></article>')

def render_archive_card(item:dict)->str:
    title=html.escape(item["title"],quote=True)
    label=html.escape(published_label(item))
    stamp=html.escape(item.get("published_iso") or item.get("first_seen") or "",quote=True)
    href=html.escape(item["url"],quote=True)
    picture=('<a href="'+href+'"><img src="'+html.escape(item["image"],quote=True)+
             '" alt="'+title+'" loading="lazy"></a>' if item["image"] else "")
    return ('<article class="news-row" data-post-category="'+item["section"]+
       '" data-published-at="'+html.escape(item.get("published_iso") or item["first_seen"],quote=True)+'">'+
       picture+'<div class="news-copy"><h2><a href="'+href+'">'+title+
       '</a></h2><div class="news-meta">ZazoomTek · <time datetime="'+stamp+'">'+label+'</time></div></div></article>')


SECTION_TARGETS={
    "speciali":("speciali.html","specialiList"),
    "extra":("extra.html","extraList"),
    "reviews":("recensioni-scritte.html","reviewList"),
}

def update_section_archives(root:Path,publications:list[dict])->dict:
    """Build independent, idempotent sections from all matched Community records.

    Stable IDs prevent duplicate cards. Every category retains its own record.
    The approved existing layout/cards remain intact outside the owned block.
    """
    written={}
    for category,(filename,element_id) in SECTION_TARGETS.items():
        page=root/filename
        if not page.is_file():
            written[category]="missing archive"
            continue
        source=page.read_text(encoding="utf-8")
        start="<!-- SERVICES10_CATEGORY_"+category.upper()+"_START -->"
        end="<!-- SERVICES10_CATEGORY_"+category.upper()+"_END -->"
        header=re.search(r'<div\b(?=[^>]*\bid=["\']'+re.escape(element_id)+r'["\'])[^>]*>',source,re.I)
        if header is None:
            written[category]="archive id not found"
            continue
        # Do not duplicate cards authored outside the managed region.
        outside=source
        if start in source and end in source:
            p=source.index(start);q=source.index(end,p)+len(end)
            outside=source[:p]+source[q:]
        matched=[p for p in publications if p["section"]==category]
        matched=deduplicate_cards(matched)
        cards=[render_archive_card(p) for p in matched
               if 'href="'+p["url"]+'"' not in outside]
        owned=start+"\n"+"\n".join(cards)+"\n"+end
        if start in source and end in source:
            first=source.index(start);last=source.index(end,first)+len(end)
            result=source[:first]+owned+source[last:]
        else:
            result=source[:header.end()]+"\n"+owned+source[header.end():]
        if result!=source:page.write_text(result,encoding="utf-8")
        written[category]=len(cards)
    return written

def update(root:Path=ROOT)->dict:
    publications=items(root)
    if not publications:return {"posts":0,"created_pages":0}
    created=0
    for post in publications:
        target=root/post["url"].lstrip("/")
        # Never overwrite an author's manually edited article.
        if not target.exists():
            target.write_text(render_detail(post),encoding="utf-8")
            created+=1
        elif target.read_text(encoding="utf-8").lstrip().startswith("<!-- SERVICES10_GENERATED -->"):
            latest=render_detail(post)
            if target.read_text(encoding="utf-8")!=latest:
                target.write_text(latest,encoding="utf-8")
    section_results=update_section_archives(root,publications)
    news=root/"news.html"
    if news.is_file():
        document=news.read_text(encoding="utf-8")
        outside=document
        if ARCH_START in outside and ARCH_END in outside:
            left=outside.index(ARCH_START);right=outside.index(ARCH_END,left)+len(ARCH_END)
            outside=outside[:left]+outside[right:]
        fresh=deduplicate_cards([p for p in publications if 'href="'+p["url"]+'"' not in outside])
        cards="\n".join(render_archive_card(p) for p in fresh)
        if ARCH_START in document and ARCH_END in document:
            updated=replace_owned(document,ARCH_START,ARCH_END,cards)
        elif cards:
            updated=re.sub(r'<article class="news-row"',
                lambda m:ARCH_START+"\n"+cards+"\n"+ARCH_END+"\n"+m.group(0),
                document,count=1)
        else:updated=document
        if updated!=document:news.write_text(updated,encoding="utf-8")
    home=root/"index.html"
    if home.is_file():
        document=home.read_text(encoding="utf-8")
        outside=document
        if HOME_START in outside and HOME_END in outside:
            left=outside.index(HOME_START);right=outside.index(HOME_END,left)+len(HOME_END)
            outside=outside[:left]+outside[right:]
        fresh=deduplicate_cards([p for p in publications if 'href="'+p["url"]+'"' not in outside])
        cards="\n".join(render_home_card(p) for p in fresh[:40])
        if HOME_START in document and HOME_END in document:
            updated=replace_owned(document,HOME_START,HOME_END,cards)
        elif cards:
            updated=document.replace("<!-- ARTICLE_FEED_START -->",
                  "<!-- ARTICLE_FEED_START -->\n"+HOME_START+"\n"+cards+"\n"+
                  HOME_END,1)
        else:updated=document
        if updated!=document:home.write_text(updated,encoding="utf-8")
    print("Community: archived",len(publications),"new pages",created,"section archives",section_results)
    return {"posts":len(publications),"created_pages":created}

if __name__=="__main__":
    update()
