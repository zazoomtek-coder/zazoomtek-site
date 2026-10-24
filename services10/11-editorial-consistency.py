#!/usr/bin/env python3
"""Routine editorial consistency: real dates, newest first, related links and rails.

This runs on the working main checkout immediately BEFORE the Cloudflare packer.
It never creates articles, changes their editorial text or invents publication
dates. All suggested links are real site article files.
"""
from __future__ import annotations
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ARCHIVES=("news.html","recensioni-tech.html","recensioni-gaming.html",
          "recensioni-scritte.html","tech-today.html","gaming-today.html",
          "speciali.html","guide.html","extra.html")
LIST_RE=re.compile(r'(?is)<div\b[^>]*\bid=["\'](?:newsList|reviewList|specialiList|guideList|extraList)["\'][^>]*>')
ROW_RE=re.compile(r'(?is)<article\b(?=[^>]*\bclass=["\'][^"\']*\bnews-row\b)[^>]*>.*?</article>')
LINK_RE=re.compile(r'(?is)<h2\b[^>]*>\s*<a\b[^>]*\bhref=["\']([^"\']+)["\'][^>]*>(.*?)</a>')
IMG_RE=re.compile(r'(?is)<img\b[^>]*\bsrc=["\']([^"\']+)["\']')
MET_RE=re.compile(r'(?is)<div\b[^>]*class=["\'][^"\']*\bnews-meta\b[^>]*>(.*?)</div>')
DATE_ISO=re.compile(r'(?<!\d)(20\d\d)-(\d\d)-(\d\d)(?:[T ][0-2]\d:[0-5]\d:[0-5]\d)?')
DATE_SLASH=re.compile(r'(?<!\d)([0-3]?\d)/([01]?\d)/(20\d\d)')
DATE_IT=re.compile(r'(?i)\b([0-3]?\d)\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(20\d\d)\b')
MONTHS={m:i+1 for i,m in enumerate(
    "gennaio febbraio marzo aprile maggio giugno luglio agosto settembre ottobre novembre dicembre".split())}
IT_MONTHS=list(MONTHS)

def plain(t):
    return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>","",t or ""))).strip()

def normal(t):
    return plain(t).casefold()

def get_date(text):
    """Only dates explicitly supplied by site metadata/author; never file mtime."""
    if not text:return ""
    s=html.unescape(str(text))
    m=DATE_ISO.search(s)
    if m:
        try:return datetime(*map(int,m.groups())).date().isoformat()
        except ValueError:pass
    m=DATE_SLASH.search(s)
    if m:
        try:return datetime(int(m[3]),int(m[2]),int(m[1])).date().isoformat()
        except ValueError:pass
    m=DATE_IT.search(s)
    if m:
        try:return datetime(int(m[3]),MONTHS[m[2].lower()],int(m[1])).date().isoformat()
        except (ValueError,KeyError):pass
    return ""

def format_date(iso):
    try:
        d=datetime.strptime(iso[:10],"%Y-%m-%d")
        return f"{d.day} {IT_MONTHS[d.month-1]} {d.year}"
    except (ValueError,IndexError,TypeError):return ""

def local_url(link):
    raw=html.unescape(link or "").split("?",1)[0].split("#",1)[0]
    if not re.fullmatch(r"/[A-Za-z0-9_.-]+\.html",raw):return ""
    if raw.startswith("/anteprima-"):return ""
    return raw

def article_metadata(root,href,cache):
    if href in cache:return cache[href]
    file=root/href.lstrip("/")
    result=("", "")
    if file.is_file():
        try:
            s=file.read_text(encoding="utf-8")
            fields=[]
            for pattern in (
                r'<meta\b[^>]*\bproperty=["\']article:published_time["\'][^>]*\bcontent=["\']([^"\']+)',
                r'<meta\b[^>]*\bname=["\'](?:datePublished|date|pubdate)["\'][^>]*\bcontent=["\']([^"\']+)',
                r'"datePublished"\s*:\s*"([^"]+)',
                r'<time\b[^>]*\bdatetime=["\']([^"\']+)',
                r'<div\b[^>]*class=["\'][^"\']*(?:article-meta|post-meta|review-meta)[^"\']*["\'][^>]*>(.*?)</div>',
            ):
                match=re.search(pattern,s,re.I|re.S)
                if match:fields.append(match.group(1))
            date=next((v for x in fields if (v:=get_date(x))),"")
            picture=""
            for regex in (
                r'<meta\b[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)',
                r'<img\b[^>]*class=["\'][^"\']*(?:article-hero|hero|cover)[^"\']*["\'][^>]*src=["\']([^"\']+)',
            ):
                m=re.search(regex,s,re.I)
                if m:
                    picture=html.unescape(m.group(1))
                    break
            result=(date,picture)
        except UnicodeError:pass
    cache[href]=result
    return result

def community_dates(root):
    try:
        posts=json.loads((root/"services10-data"/"community.json").read_text(encoding="utf-8"))
        return {"/news-"+p["id"]+".html":get_date(p.get("published_iso") or p.get("first_seen"))
                for p in posts if isinstance(p,dict) and p.get("id")}
    except (OSError,ValueError,TypeError,KeyError):return {}

def extract_rows(root,cache,community):
    stories={}
    for section in ARCHIVES:
        page=root/section
        if not page.is_file():continue
        s=page.read_text(encoding="utf-8")
        match=LIST_RE.search(s)
        if not match:continue
        # Editorial rows only, not sidebar or navigation
        stop=s.find("<!-- ZT_COMMUNITY_BANNER_START -->",match.end())
        if stop<0:stop=s.find("<aside",match.end())
        if stop<0:stop=len(s)
        for rm in ROW_RE.finditer(s,match.end(),stop):
            card=rm.group(0)
            m=LINK_RE.search(card)
            if not m:continue
            href=local_url(m.group(1))
            if not href or not (root/href.lstrip("/")).is_file():continue
            title=plain(m.group(2))
            if not title:continue
            meta=MET_RE.search(card)
            date=get_date(re.search(r'data-published-at=["\']([^"\']+)',card).group(1)
                          if re.search(r'data-published-at=["\']([^"\']+)',card) else "")
            if not date:date=get_date(meta.group(1)) if meta else ""
            filedate,poster=article_metadata(root,href,cache)
            if not date:date=community.get(href) or filedate
            pic=IMG_RE.search(card)
            cover=html.unescape(pic.group(1)) if pic else poster
            # No generic placeholder images in recommendations.
            if cover.startswith("/") and not (root/cover.lstrip("/")).is_file():cover=poster
            if not cover.startswith(("https://","/")):cover=poster
            category=("gaming" if section in ("recensioni-gaming.html","gaming-today.html") else
                      "tech" if section in ("recensioni-tech.html","tech-today.html") else
                      "special" if section=="speciali.html" else
                      "reviews" if section=="recensioni-scritte.html" else
                      "general")
            candidate=dict(href=href,title=title,date=date,img=cover,category=category,section=section)
            previous=stories.get(href)
            if previous is None or (candidate["date"] and not previous["date"]):
                stories[href]=candidate
    return stories

def display_date_row(card, date):
    if not date:return card
    label=format_date(date)
    if not label:return card
    prior=MET_RE.search(card)
    if prior:
        old=plain(prior.group(1))
        suffix=""
        # Preserve meaningful platform/category, not stale relative dates.
        for part in old.split("·")[1:]:
            v=part.strip()
            if v and not get_date(v) and not re.search(r"(?i)\b(?:fa|modificat|ore|giorni|settiman)\b",v):
                suffix+=" · "+html.escape(v)
        new='<div class="news-meta">ZazoomTek · <time datetime="'+date+'">'+label+"</time>"+suffix+"</div>"
        card=card[:prior.start()]+new+card[prior.end():]
    else:
        link=LINK_RE.search(card)
        if link:
            injection='<div class="news-meta">ZazoomTek · <time datetime="'+date+'">'+label+"</time></div>"
            card=card[:link.end()]+injection+card[link.end():]
    if not re.search(r'\bdata-published-at=',card[:400]):
        card=re.sub(r'(<article\b)',r'\1 data-published-at="'+date+'"',card,count=1)
    return card

def sort_archive(root,path,stories,cache,community):
    s=path.read_text(encoding="utf-8")
    match=LIST_RE.search(s)
    if not match:return False,0
    stop=s.find("<!-- ZT_COMMUNITY_BANNER_START -->",match.end())
    if stop<0:stop=s.find("<aside",match.end())
    if stop<0:stop=len(s)
    region=s[match.end():stop]
    rows=list(ROW_RE.finditer(region))
    if len(rows)<1:return False,0
    used=set();ordered=[]
    for index,m in enumerate(rows):
        card=m.group(0);link=LINK_RE.search(card)
        if not link:continue
        href=local_url(link.group(1))
        if not href:continue
        story=stories.get(href)
        date=(story or {}).get("date") or community.get(href) or article_metadata(root,href,cache)[0]
        title=normal(link.group(2))
        if not title or href in used:continue
        used.add(href)
        ordered.append((date or "",-index,display_date_row(card,date)))
    # Keep slots and intervening section markup/comments intact.
    ordered.sort(key=lambda v:(v[0],v[1]),reverse=True)
    new=region
    for old,rec in reversed(list(zip(rows,ordered))):
        new=new[:old.start()]+rec[2]+new[old.end():]
    updated=s[:match.end()]+new+s[stop:]
    if updated!=s:path.write_text(updated,encoding="utf-8")
    return updated!=s,len(ordered)

def related_block(stories,current,root,limit=4):
    category=current.get("category","general")
    pool=[s for s in stories.values() if s["href"]!=current["href"] and s["img"]
          and (root/s["href"].lstrip("/")).is_file()]
    pool.sort(key=lambda v:(v["category"]==category,v["date"] or ""),reverse=True)
    dedup=set();cards=[]
    for s in pool:
        k=normal(s["title"])
        if k in dedup:continue
        dedup.add(k)
        title=html.escape(s["title"],quote=True);url=html.escape(s["href"],quote=True)
        image=html.escape(s["img"],quote=True)
        when=('<time datetime="'+s["date"]+'">'+format_date(s["date"])+'</time>') if s["date"] else ""
        cards.append('<a class="zt-ec-related-card" href="'+url+'"><img src="'+image+
                     '" alt="'+title+'" loading="lazy"><strong>'+title+'</strong>'+when+'</a>')
        if len(cards)>=limit:break
    if not cards:return ""
    return ('<!-- ZT_EDITORIAL_RELATED_START --><section class="zt-ec-related" aria-label="Articoli correlati">'
            '<h2>ARTICOLI CORRELATI</h2><div class="zt-ec-related-grid">'+
            "".join(cards)+'</div></section><!-- ZT_EDITORIAL_RELATED_END -->')

def rail_html(stories,current,root):
    section=current.get("category","general")
    pool=[s for s in stories.values() if s["href"]!=current["href"] and s["img"]
          and (root/s["href"].lstrip("/")).is_file()]
    pool.sort(key=lambda x:(x["category"]==section,x["date"] or ""),reverse=True)
    used=set();blocks=[]
    for group,title in (("general","Ultime notizie"),("reviews","Recensioni"),
                        ("special","Speciali e Insights")):
        candidates=[]
        # Reviews can be Tech and Gaming reviews.
        matches=[s for s in pool if (s["category"] in ("reviews","gaming","tech")
                  and "recensioni" in s["section"]) if group=="reviews"] if group=="reviews" else [
                  s for s in pool if (s["category"]=="special" if group=="special"
                                      else s["category"]=="general")]
        for x in matches:
            key=normal(x["title"])
            if x["href"] in used or key in used:continue
            used.add(x["href"]);used.add(key)
            name=html.escape(x["title"]);url=html.escape(x["href"],quote=True)
            stamp=('<time datetime="'+x["date"]+'">'+format_date(x["date"])+'</time>') if x["date"] else ""
            candidates.append('<a class="zt-ec-rail-card" href="'+url+'"><img src="'+
                              html.escape(x["img"],quote=True)+'" alt="'+name+
                              '" loading="lazy"><span><strong>'+name+'</strong>'+stamp+'</span></a>')
            if len(candidates)==5:break
        if candidates:
            blocks.append('<section class="side-box zt-ec-rail-box"><h2>'+title+
                          '</h2>'+''.join(candidates)+'</section>')
    return '<!-- ZT_EDITORIAL_RAIL_START -->'+"".join(blocks)+'<!-- ZT_EDITORIAL_RAIL_END -->'

STYLE="""<style id="zt-editorial-consistency-style">
.zt-ec-related{clear:both;margin:30px 0;padding:22px 0 0;border-top:3px solid #d51232}
.zt-ec-related>h2{background:#191919;color:white;font:800 17px Arial,sans-serif;
margin:0 0 15px;padding:13px 17px;border-radius:0!important;clip-path:none!important}
.zt-ec-related-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
.zt-ec-related-card{display:block;border:1px solid #e2e2e2;text-decoration:none;color:#222;
overflow:hidden;background:white}
.zt-ec-related-card img{display:block;width:100%;aspect-ratio:16/9;object-fit:cover}
.zt-ec-related-card strong{display:block;padding:9px 10px 2px;font:700 14px/1.35 Arial,sans-serif}
.zt-ec-related-card time{display:block;padding:3px 10px 10px;color:#777;font:12px Arial,sans-serif}
.zt-ec-rail-box{background:white;margin-bottom:18px;border:1px solid #ddd}
.zt-ec-rail-box>h2{margin:0;background:#191919;color:white!important;clip-path:none!important;
border-radius:0!important;padding:12px;font:800 15px Arial,sans-serif}
.zt-ec-rail-card{display:grid;grid-template-columns:95px minmax(0,1fr);gap:10px;padding:10px;
text-decoration:none;color:#222;border-bottom:1px solid #eee}
.zt-ec-rail-card img{width:95px;aspect-ratio:16/9;object-fit:cover}
.zt-ec-rail-card strong{display:block;font:700 12px/1.35 Arial,sans-serif}
.zt-ec-rail-card time{display:block;font:11px Arial,sans-serif;color:#777;margin-top:5px}
.zt-ec-article-date{display:block;margin:12px 0 20px;color:#777;font:14px Arial,sans-serif}
main:has(>.zt-ec-auto-rail){display:grid;grid-template-columns:minmax(0,1fr) 288px;
gap:16px;align-items:start;max-width:1250px;margin-inline:auto}
main:has(>.zt-ec-auto-rail)>.zt-ec-auto-rail{min-width:0}
@media(max-width:800px){main:has(>.zt-ec-auto-rail){display:block}
.zt-ec-related-grid{grid-template-columns:1fr}}
</style>"""

def update_detail(root,page,stories,cache,community):
    name=page.name
    if (name in ARCHIVES or name=="index.html" or name.startswith("anteprima-") or
        name.startswith(("watch-","news-2.")) or page.parts[-2:-1]==("studio",)):
        return False
    doc=page.read_text(encoding="utf-8")
    if "<main" not in doc.lower() or not re.search(r"<h1\b",doc,re.I):return False
    if not re.search(r"</article>",doc,re.I) and not re.search(r"</main>",doc,re.I):return False
    href="/"+name
    current=stories.get(href) or {"href":href,"title":name,"date":"","category":"general"}
    date=current["date"] or community.get(href) or article_metadata(root,href,cache)[0]
    changed=doc
    # Rebuild only our own previously generated widgets; keep hand-designed ones.
    changed=re.sub(r'(?s)<!-- ZT_EDITORIAL_RELATED_START -->.*?<!-- ZT_EDITORIAL_RELATED_END -->',"",changed)
    changed=re.sub(r'(?s)<!-- ZT_EDITORIAL_RAIL_START -->.*?<!-- ZT_EDITORIAL_RAIL_END -->',"",changed)
    changed=re.sub(r'(?s)<style id="zt-editorial-consistency-style">.*?</style>',"",changed)
    if "</head>" in changed:changed=changed.replace("</head>",STYLE+"\n</head>",1)
    if date and not re.search(r'zt-ec-article-date',changed):
        headline=re.search(r'(?is)<h1\b[^>]*>.*?</h1>',changed)
        if headline:
            meta='<div class="zt-ec-article-date">Pubblicato il <time datetime="'+date+'">'+format_date(date)+'</time></div>'
            # If author already printed a real publish date next to H1, don't duplicate.
            subsequent=plain(changed[headline.end():headline.end()+900])
            if format_date(date).lower() not in subsequent.lower():
                changed=changed[:headline.end()]+meta+changed[headline.end():]
    if 'zt-related-section' not in changed and 'RELATED_CONTENT_START' not in changed:
        related=related_block(stories,current,root)
        if related:
            e=re.search(r'</article>',changed,re.I)
            if e:changed=changed[:e.start()]+related+changed[e.start():]
            else:changed=changed.replace("</main>",related+"</main>",1)
    rail=rail_html(stories,current,root)
    aside=re.search(r'<aside\b[^>]*class=["\'][^"\']*(?:news-sidebar|article-side)[^"\']*["\'][^>]*>',changed,re.I)
    if aside:
        end=changed.find("</aside>",aside.end())
        if end>=0:changed=changed[:end]+rail+changed[end:]
    elif "</main>" in changed:
        changed=changed.replace("</main>",'<aside class="zt-ec-auto-rail">'+rail+'</aside></main>',1)
    if changed!=doc:page.write_text(changed,encoding="utf-8")
    return changed!=doc

def update(root=ROOT):
    cache={}; community=community_dates(root)
    stories=extract_rows(root,cache,community)
    counters={"archives":0,"archive_cards":0,"details":0,"stories":len(stories)}
    for filename in ARCHIVES:
        file=root/filename
        if not file.is_file():continue
        changed,n=sort_archive(root,file,stories,cache,community)
        counters["archives"]+=int(changed);counters["archive_cards"]+=n
    for page in root.glob("*.html"):
        if page.name.startswith("news-") and re.match(r"news-\d+\.html",page.name):continue
        counters["details"]+=int(update_detail(root,page,stories,cache,community))
    print("Editorial consistency: ",counters)
    return counters

if __name__=="__main__":update()
