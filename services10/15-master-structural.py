#!/usr/bin/env python3
"""MASTER pre-deploy normalizer for the generated Cloudflare snapshot.

Never modifies individual original articles: only dist/ HTML and generated
manifests. Guarantees a common template, deduplication and latest-first lists.
Requires only Python's standard library. No replacement of author text.
"""
from __future__ import annotations
import html
import json
import math
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/"dist"
START="<!-- ZT_MASTER_SIDEBAR_START -->"
END="<!-- ZT_MASTER_SIDEBAR_END -->"
HEAD='<link rel="stylesheet" href="/zt-master-template.css?v=20261024">'
HEAD_JS='<script defer src="/zt-master-template.js?v=20261024"></script>'
MARKERS=("ARTICLE_FEED_START","SERVICES10_COMMUNITY_HOME_START","SERVICES10_COMMUNITY_ARCHIVE_START")
MONTHS={"gennaio":1,"febbraio":2,"marzo":3,"aprile":4,"maggio":5,
        "giugno":6,"luglio":7,"agosto":8,"settembre":9,"ottobre":10,
        "novembre":11,"dicembre":12}
ROW=re.compile(r'(?is)<article\b[^>]*\bclass=["\'][^"\']*\b(?:news-row|article-row)\b[^"\']*["\'][^>]*>.*?</article>')
LINK=re.compile(r'(?is)<a\b[^>]*\bhref=["\']([^"\']+)["\'][^>]*>')
TAG=re.compile(r'<[^>]*>')
TITLE=re.compile(r'(?is)<h1\b[^>]*>(.*?)</h1>')
META=re.compile(r'(?is)<meta\b[^>]*>')
IMAGE=re.compile(r'(?is)<img\b[^>]*\bsrc=["\']([^"\']+)')
DATE=re.compile(r'20\d\d-\d\d-\d\d')

def text(value):
    return re.sub(r"\s+"," ",html.unescape(TAG.sub("",str(value or "")))).strip()

def norm(value):
    return re.sub(r"[^\w]+"," ",text(value).casefold()).strip()

def urlkey(value):
    path=urlparse(html.unescape(value or "")).path
    path=("/"+path.lstrip("/")).lower()
    if path.endswith("/"):path+="index.html"
    return path

def timestamp(value):
    if not value:return ""
    match=DATE.search(str(value))
    if match:
        try:return date.fromisoformat(match.group(0)).isoformat()
        except ValueError:return ""
    match=re.search(r'(\d\d?)\s+('+"|".join(MONTHS)+r')\s+(20\d\d)',str(value),re.I)
    if match:
        try:return date(int(match[3]),MONTHS[match[2].lower()],int(match[1])).isoformat()
        except ValueError:return ""
    return ""

def attrs(tag):
    return {key.lower():html.unescape(value) for key,_,value in re.findall(
        r'([:\w-]+)\s*=\s*(["\'])(.*?)\2',tag,re.S)}

def source_info(page):
    content=page.read_text(encoding="utf-8",errors="replace")
    heading=TITLE.search(content)
    title=text(heading.group(1)) if heading else ""
    metadata=[attrs(t.group()) for t in META.finditer(content[:content.lower().find("</head>") if "</head>" in content.lower() else 9000])]
    image="";published="";category=""
    for m in metadata:
        if m.get("property")=="og:image" and not image:image=m.get("content","")
        if m.get("property")=="article:published_time" and not published:published=timestamp(m.get("content"))
        if m.get("name") in ("date","datePublished","pubdate") and not published:published=timestamp(m.get("content"))
    if not published:
        explicit=re.search(r'(?is)<time\b[^>]*datetime=["\']([^"\']+)',content)
        if explicit:published=timestamp(explicit.group(1))
    if not published:
        schema=re.search(r'["\']datePublished["\']\s*:\s*["\']([^"\']+)',content,re.I)
        if schema:published=timestamp(schema.group(1))
    if not image:
        main=re.search(r'<main\b',content,re.I)
        fragment=content[main.start():] if main else ""
        for img in re.finditer(r'<img\b[^>]*>',fragment,re.I):
            d=attrs(img.group())
            if any(x in d.get("class","") for x in ("hero","cover","article-image")):
                image=d.get("src","");break
    if image.startswith("/") and not (DIST/image.lstrip("/")).is_file():image=""
    if not image.startswith(("https://","/")) or "ChatGPT.png" in image:image=""
    if "recensione" in page.stem.lower():category="reviews"
    elif "gaming" in page.stem.lower():category="gaming"
    elif "tech" in page.stem.lower():category="tech"
    return {"url":"/"+page.relative_to(DIST).as_posix(),"title":title,
            "image":image,"published":published,"category":category}

def read_json(path):
    try:return json.loads(path.read_text(encoding="utf-8"))
    except (OSError,ValueError):return []

def keep_latest(entries):
    """Canonical URL plus normalized title; first/newest wins."""
    entries=sorted((v for v in entries if isinstance(v,dict)),
                   key=lambda v:(v.get("published") or v.get("publishedAt") or "",v.get("url") or ""),reverse=True)
    used_urls=set();used_titles=set();result=[]
    for item in entries:
        u=urlkey(item.get("url") or ("/watch/"+str(item.get("id") or "")+".html"))
        name=norm(item.get("title",""))
        if not name or u in used_urls or name in used_titles:continue
        result.append(item);used_urls.add(u);used_titles.add(name)
    return result

def collect():
    records=[]
    for page in DIST.glob("*.html"):
        if page.name in ("index.html","ecoturismo.html","studio.html") or page.name.startswith(("anteprima-","recensioni-","watch-")):continue
        record=source_info(page)
        if record["title"] and record["image"]:records.append(record)
    community=read_json(ROOT/"services10-data"/"community.json")
    for item in community if isinstance(community,list) else []:
        pid=str(item.get("id") or "")
        if not re.fullmatch(r"Ugkx[A-Za-z0-9_-]{3,100}",pid):continue
        path=DIST/("news-"+pid+".html")
        if not path.is_file():continue
        record={"url":"/"+path.name,"title":item.get("title") or "",
                "image":item.get("image") or ((item.get("images") or [""])[0]),
                "published":timestamp(item.get("published_iso") or item.get("first_seen")),
                "category":"gaming" if re.match(r'(?i)^news gaming',item.get("title") or "")
                else "tech" if re.match(r'(?i)^news tech',item.get("title") or "") else "news"}
        if record["image"] and record["title"]:records.append(record)
    # Include existing archive records even when metadata is thin.
    for name in ("news.html","recensioni-tech.html","recensioni-gaming.html",
                 "tech-today.html","gaming-today.html","speciali.html"):
        path=DIST/name
        if not path.is_file():continue
        for m in ROW.finditer(path.read_text(encoding="utf-8",errors="replace")):
            article=m.group()
            link=re.search(r'(?is)<h[23]\b[^>]*>\s*<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',article)
            image=IMAGE.search(article)
            if not link or not image:continue
            target=urlkey(link.group(1))
            if not (DIST/target.lstrip("/")).is_file():continue
            record={"url":target,"title":text(link.group(2)),"image":html.unescape(image.group(1)),
                    "published":timestamp(article),
                    "category":"gaming" if ("gaming" in name or 'data-post-category="gaming"' in article)
                    else "tech" if ("tech" in name or 'data-post-category="tech"' in article)
                    else "reviews" if "recensioni" in name else "news"}
            if record["title"] and record["image"]:records.append(record)
    return keep_latest(records)

def dedup_catalog():
    path=DIST/"home-video-feed.json"
    data=read_json(path)
    if isinstance(data,list):
        unique={}
        for item in data:
            if not isinstance(item,dict):continue
            ident=str(item.get("id") or "")
            if not re.fullmatch(r"[A-Za-z0-9_-]{11}",ident):continue
            prev=unique.get(ident)
            if prev is None or (item.get("publishedAt") or "")>(prev.get("publishedAt") or ""):
                unique[ident]=item
        clean=sorted(unique.values(),key=lambda x:x.get("publishedAt") or "",reverse=True)
        if clean!=data:path.write_text(json.dumps(clean,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        return len(data)-len(clean)
    return 0

def dedup_region(doc,open_mark,close_mark):
    a="<!-- "+open_mark+" -->";b="<!-- "+close_mark+" -->"
    if a not in doc or b not in doc:return doc,0
    start=doc.index(a)+len(a);stop=doc.index(b,start)
    section=doc[start:stop]
    rows=list(ROW.finditer(section))
    if not rows:return doc,0
    seen_urls=set();seen_titles=set();ordered=[];removed=0
    for i,m in enumerate(rows):
        card=m.group()
        link=LINK.search(card)
        title=re.search(r'(?is)<h[23]\b[^>]*>(.*?)</h[23]>',card)
        linkkey=urlkey(link.group(1)) if link else ""
        name=norm(title.group(1)) if title else ""
        if not linkkey or linkkey in seen_urls or (name and name in seen_titles):
            removed+=1;continue
        seen_urls.add(linkkey)
        if name:seen_titles.add(name)
        date_match=re.search(r'\bdata-published-at=["\']([^"\']+)',card)
        stamp=timestamp(date_match.group(1)) if date_match else timestamp(card)
        ordered.append((stamp,-i,card))
    ordered.sort(key=lambda x:(x[0],x[1]),reverse=True)
    new=section
    replacements=[v[2] for v in ordered]+[""]*removed
    for original,replacement in reversed(list(zip(rows,replacements))):
        new=new[:original.start()]+replacement+new[original.end():]
    return doc[:start]+new+doc[stop:],removed

def fresh(entries,section=None):
    cutoff=(datetime.now(timezone.utc).date()-timedelta(days=2)).isoformat()
    return [s for s in entries if (not section or s.get("category")==section)
            and s.get("published","")>=cutoff and s["image"]]

def featured(entries):
    recent=fresh(entries)
    selection=[];used=set()
    for category,n in (("tech",4),("gaming",1)):
        for s in recent:
            if s["category"]!=category or s["url"] in used:continue
            used.add(s["url"]);selection.append(s)
            if len([x for x in selection if x["category"]==category])>=n:break
    return selection

def feature_card(item):
    title=html.escape(item["title"],quote=True)
    return ('<a class="zt-feature-card zt-feature-small" data-feature-section="'+
            html.escape(item["category"])+'" href="'+html.escape(item["url"],quote=True)+
            '" title="'+title+'" aria-label="'+title+'"><img src="'+
            html.escape(item["image"],quote=True)+'" alt="'+title+'" loading="lazy"></a>')

def popular_card(item):
    name=html.escape(item["title"],quote=True)
    return ('<a class="zt-popular-article" href="'+html.escape(item["url"],quote=True)+
            '" title="'+name+'"><img src="'+html.escape(item["image"],quote=True)+
            '" alt="'+name+'" loading="lazy"><span class="zt-popular-copy">'+
            '<span class="zt-popular-category">TECNOLOGIA</span><strong>'+
            name+'</strong></span></a>')

def replace_between(doc,first,last,payload):
    a="<!-- "+first+" -->";b="<!-- "+last+" -->"
    if a not in doc or b not in doc:return doc
    begin=doc.index(a)+len(a);end=doc.index(b,begin)
    return doc[:begin]+"\n"+payload+"\n"+doc[end:]

def master_home(doc,items):
    # Deduplicate and date-order independent content feeds before selecting Home boxes.
    total=0
    for opening,closing in (
        ("SERVICES10_COMMUNITY_HOME_START","SERVICES10_COMMUNITY_HOME_END"),
        ("ARTICLE_FEED_START","ARTICLE_FEED_END")):
        doc,removed=dedup_region(doc,opening,closing);total+=removed
    hero=featured(items)
    if hero:doc=replace_between(doc,"FEATURED_NEWS_START","FEATURED_NEWS_END",
                                '<div class="zt-featured-grid" id="ztFeaturedGrid">'+
                                "".join(feature_card(x) for x in hero)+"</div>")
    used={v["url"] for v in hero}
    popular=[]
    for s in fresh(items,"tech"):
        if s["url"] in used:continue
        popular.append(s);used.add(s["url"])
        if len(popular)==5:break
    doc=replace_between(doc,"POPULAR_NEWS_ITEMS_START","POPULAR_NEWS_ITEMS_END",
                        "".join(popular_card(s) for s in popular))
    return doc,total,hero

def sidebar(items,current,main):
    pool=[s for s in items if s["url"]!=current and s["image"]]
    # deterministic diversity based on stable URL, latest content first.
    words=max(1,len(text(main)))
    limit=min(max(10,math.ceil(words/180)),max(0,len(pool)-4))
    chosen=pool[:limit]
    related=pool[limit:limit+4]
    def card(s):
        return '<a class="zt-master-card" href="'+html.escape(s["url"],quote=True)+'"><img src="'+html.escape(s["image"],quote=True)+'" loading="lazy" alt="'+html.escape(s["title"],quote=True)+'"><span>'+html.escape(s["title"])+'</span></a>'
    groups=[]
    for n in range(0,len(chosen),6):
        group=chosen[n:n+6]
        heading="ULTIME NOTIZIE" if n==0 else "DALLA REDAZIONE"
        groups.append('<section class="zt-master-group"><h2>'+heading+'</h2><div class="zt-master-grid">'+
                      "".join(card(s) for s in group)+'</div></section>')
    correlati='<section class="zt-master-related"><h2>ARTICOLI CORRELATI</h2><div class="zt-master-grid">'+\
        "".join(card(s) for s in related)+'</div></section>'
    return START+'<aside class="zt-master-rail" aria-label="Box editoriali e articoli correlati">'+\
           "".join(groups)+correlati+'</aside>'+END

def add_class(tag,cls):
    """Add a CSS class without emitting a second HTML class attribute."""
    found=re.search(r"""class=(["'])(.*?)\1""",tag,re.I|re.S)
    if found:
        existing=found.group(2).split()
        if cls not in existing:existing.append(cls)
        return tag[:found.start()]+'class="'+html.escape(" ".join(existing),quote=True)+'"'+tag[found.end():]
    return tag[:-1]+' class="'+cls+'">' if tag.endswith(">") else tag

def update_main_class(doc):
    return re.sub(r'(?i)<main\b[^>]*>',lambda m:add_class(m.group(0),"zt-master-layout"),doc,count=1)

def dedup_archive_cards(doc):
    """Collapse exact repeated story rows in archive outputs; no article-body edits."""
    if not re.search(r"""\bid=["'](?:newsList|reviewList|specialiList|guideList|extraList)["']""",doc):
        return doc,0
    rows=list(ROW.finditer(doc))
    seen_urls=set();seen_titles=set();removed=0;out=doc
    # Keep the earliest card after the upstream newest-first sort.
    for match in reversed(rows):
        card=match.group(0)
        head=re.search(r"""(?is)<h[23]\b[^>]*>\s*<a\b[^>]*href=["']([^"']+)["'][^>]*>(.*?)</a>""",card)
        if not head:continue
        url=urlkey(head.group(1));name=norm(head.group(2))
        if url in seen_urls or (name and name in seen_titles):
            out=out[:match.start()]+out[match.end():];removed+=1
        else:
            seen_urls.add(url)
            if name:seen_titles.add(name)
    return out,removed


def full_page(doc,page,items,header):
    if not re.search(r"(?is)<main\b",doc):return doc,False
    if page.name=="index.html":
        # Preserve the approved Home masthead/ticker; add the new official section.
        if 'href="/ecoturismo.html"' not in doc:
            doc=doc.replace('<a href="/extra.html">Extra</a>',
                '<a href="/extra.html">Extra</a><a href="/ecoturismo.html">Ecoturismo</a>',1)
        return doc,True
    # No nested legacy header survives in article output.
    first_header=re.search(r'<header\b',doc,re.I)
    first_main=re.search(r'<main\b',doc,re.I)
    if not first_header or (first_main and first_header.start()>first_main.start()):
        doc=re.sub(r'(?i)<body\b[^>]*>',lambda m:m.group()+"\n"+header,doc,count=1)
    else:
        doc=re.sub(r'(?is)<header\b[^>]*>.*?</header>',lambda _:header,doc,count=1)
    # Remove legacy generated sidebars and replace with one global instance.
    doc=re.sub(r'(?s)<!-- ZT_UNIFIED_EDITORIAL_START -->.*?<!-- ZT_UNIFIED_EDITORIAL_END -->',"",doc)
    doc=re.sub(r'(?s)<!-- ZT_EDITORIAL_RAIL_START -->.*?<!-- ZT_EDITORIAL_RAIL_END -->',"",doc)
    doc=re.sub(r'(?s)<!-- ZT_MASTER_SIDEBAR_START -->.*?<!-- ZT_MASTER_SIDEBAR_END -->',"",doc)
    # Handle sidebars generated earlier by any renderer. Avoid changing article body.
    existing=re.search(r'(?is)<aside\b[^>]*class=["\'][^"\']*(?:news-sidebar|article-side|zt-ec-auto-rail|zt-unified-editorial-aside)[^"\']*["\'][^>]*>.*?</aside>',doc)
    main_match=re.search(r'(?is)<main\b[^>]*>',doc)
    if not main_match:return doc,False
    main_close=doc.find("</main>",main_match.end())
    if main_close<0:return doc,False
    content=doc[main_match.end():main_close]
    box=sidebar(items,"/"+page.relative_to(DIST).as_posix(),content)
    if existing:
        # If <aside> was outside main, the surrounding .layout becomes the grid.
        at=existing.start()
        doc=doc[:at]+box+doc[existing.end():]
        parent=re.search(r'(?is)<(?:div|section)\b[^>]*class=["\'][^"\']*(?:layout|detail-grid|news-layout)[^"\']*["\'][^>]*>',doc)
        if parent:
            opening=parent.group()
            doc=doc[:parent.start()]+add_class(opening,"zt-master-layout")+doc[parent.end():]
        else:
            # If no recognizable grid parent, move the aside inside main.
            doc=doc.replace(box,"",1)
            doc=doc.replace("</main>",box+"</main>",1)
            doc=update_main_class(doc)
    else:
        doc=doc[:main_close]+box+doc[main_close:]
        doc=update_main_class(doc)
    return doc,True

def ecoturismo_page(items):
    path=DIST/"ecoturismo.html"
    if path.exists():return
    selections=[x for x in items if re.search(r"ecoturism|sostenibil|ambient|green tech",x["title"],re.I)]
    cards="".join('<p><a href="'+html.escape(x["url"])+'">'+html.escape(x["title"])+"</a></p>" for x in selections)
    if not cards:cards="<p>La sezione Ecoturismo raccoglierà i prossimi approfondimenti dedicati a sostenibilità, tecnologia e viaggi responsabili.</p>"
    path.write_text('<!doctype html><html lang="it"><head><meta charset="utf-8">'+
       '<meta name="viewport" content="width=device-width,initial-scale=1">'+
       '<title>Ecoturismo | ZazoomTek</title><meta name="robots" content="index,follow">'+
       '</head><body><main><article class="article-main"><h1>ECOTURISMO</h1>'+cards+
       '</article></main></body></html>',encoding="utf-8")

def run():
    if not (DIST/"index.html").is_file():raise SystemExit("Snapshot dist/ mancante")
    header=(ROOT/"zt-master-header.html").read_text(encoding="utf-8").strip()
    removed_videos=dedup_catalog()
    items=collect()
    ecoturismo_page(items)
    (DIST/"zt-sidebar-feed.json").write_text(
        json.dumps({"news":[{"url":x["url"],"title":x["title"],"image":x["image"],
                            "published":x["published"]} for x in items]},ensure_ascii=False)+"\n",encoding="utf-8")
    pages=0;home_dupes=0;hero=[]
    for page in DIST.rglob("*.html"):
        if page.relative_to(DIST).parts[0] in ("studio",) or page.name=="zt-master-header.html":
            continue
        doc=page.read_text(encoding="utf-8",errors="replace")
        if page.name=="index.html" and page.parent==DIST:
            doc,home_dupes,hero=master_home(doc,items)
        elif page.parent==DIST:
            doc,removed=dedup_archive_cards(doc)
            home_dupes+=removed
        doc,handled=full_page(doc,page,items,header)
        if not handled:continue
        if HEAD not in doc:doc=doc.replace("</head>",HEAD+"\n</head>",1)
        if HEAD_JS not in doc:doc=doc.replace("</body>",HEAD_JS+"\n</body>",1)
        doc=re.sub(r'(?i)<body(?=[\s>])',lambda m:m.group()+" class=\"zt-master-page\"" if "zt-master-page" not in doc[:doc.find("<body")+100] else m.group(),doc,count=1)
        page.write_text(doc,encoding="utf-8")
        pages+=1
    print("MASTER STRUCTURAL:",{"pages_with_template":pages,
        "unique_editorial_records":len(items),"home_duplicates_removed":home_dupes,
        "featured_current":len(hero),"video_duplicates_removed":removed_videos})
    return pages

if __name__=="__main__":run()
