#!/usr/bin/env python3
"""Route already imported YouTube Tech Impact / Gaming Inside posts to their
dedicated archives. Never rewrite the Home, source articles, or featured slots.

Both the Community importer and the independent special-news publisher use this
same idempotent merge, so one publisher cannot make the other's cards vanish.
"""
from __future__ import annotations
from datetime import datetime, timezone
from html import escape, unescape
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
SECTIONS={"tech-impact":("tech","tech-today.html"),
          "gaming-inside":("gaming","gaming-today.html")}
LABEL=re.compile(r"^News\s+(Tech\s+Impact|Gaming\s+Inside)\s*:\s*(.+)$",re.I|re.S)
ARTICLE=re.compile(r'<article\b[^>]*class="[^"]*\bnews-row\b[^"]*"[^>]*>[\s\S]*?</article>',re.I)
META_TIME=re.compile(r'<meta\b[^>]*property="article:published_time"[^>]*content="([^"]+)"',re.I)
H1=re.compile(r"<h1\b[^>]*>(.*?)</h1>",re.I|re.S)
HERO=re.compile(r'<img\b[^>]*class="[^"]*\barticle-hero\b[^"]*"[^>]*src="([^"]+)"',re.I)
INTRO=re.compile(r'<div\b[^>]*class="article-body"[^>]*>\s*<p[^>]*>(.*?)</p>',re.I|re.S)
HREF=re.compile(r'<a\b[^>]*href="(/[^"]+\.html)"',re.I)
DATE=re.compile(r'<div\b[^>]*class="news-meta"[^>]*>\s*ZazoomTek\s*·\s*([^<]+)</div>',re.I)
SENTINEL="<!-- ZT_COMMUNITY_BANNER_START -->"

def clean(value:str)->str:
    return " ".join(unescape(re.sub(r"<[^>]*>","",value)).split())

def instant(value:str)->float:
    try:
        timestamp=datetime.fromisoformat(value.strip().replace("Z","+00:00"))
        if timestamp.tzinfo is None:timestamp=timestamp.replace(tzinfo=timezone.utc)
        return timestamp.timestamp()
    except (ValueError,TypeError,OverflowError):
        return 0.0

def community_rows(root:Path):
    result={"tech":[],"gaming":[]}
    routes={}
    for page in sorted(root.glob("news-Ugkx*.html")):
        src=page.read_text(encoding="utf-8",errors="replace")
        header=H1.search(src)
        if not header:continue
        match=LABEL.fullmatch(clean(header.group(1)))
        if not match:continue
        section=("tech" if match.group(1).lower().startswith("tech") else "gaming")
        url="/"+page.name
        title=match.group(2).strip()
        date_match=META_TIME.search(src)
        hero=HERO.search(src)
        intro=INTRO.search(src)
        if not date_match or not instant(date_match.group(1)) or not hero:
            raise RuntimeError(f"Community special article has incomplete metadata: {page.name}")
        image=unescape(hero.group(1)).strip()
        if not image.startswith(("https://","/assets/")):
            raise RuntimeError(f"Community special article has invalid image: {page.name}")
        when=instant(date_match.group(1))
        date=datetime.fromtimestamp(when,timezone.utc).date().isoformat()
        summary=clean(intro.group(1))[:290] if intro else ""
        entry=(f'<article class="news-row" data-zt-source="community-special">'
               f'<a href="{escape(url,quote=True)}"><img src="{escape(image,quote=True)}" alt="{escape(title,quote=True)}" loading="lazy"></a>'
               f'<div class="news-copy"><h2><a href="{escape(url,quote=True)}">{escape(title)}</a></h2>'
               f'<div class="news-meta">ZazoomTek · {date}</div>'
               f'<p>{escape(summary)}</p><a class="news-read" href="{escape(url,quote=True)}">Leggi tutto</a></div></article>')
        routes[url]=section
        result[section].append((when,url,entry))
    return result,routes

def merge_category(root:Path,category:str,archive:str,additions,routes):
    file=root/archive
    src=file.read_text(encoding="utf-8")
    start_tag=f'<div class="news-list" id="newsList" data-auto-articles="{category}">'
    if src.count(start_tag)!=1:
        raise RuntimeError(f"Archive marker missing or duplicated: {archive}")
    start=src.index(start_tag)+len(start_tag)
    # Close the WHOLE archive list, not the first nested news-copy <div>.
    # The independent publisher guarantees this exact banner boundary.
    finish=re.search(r'</div>(?=\s*(?:<!-- ZT_COMMUNITY_BANNER_START -->|</section>))',src[start:],re.I)
    if not finish:
        raise RuntimeError(f"Archive / Community banner structure invalid: {archive}")
    end=start+finish.start()
    if SENTINEL not in src[end:]:
        raise RuntimeError(f"Archive lost its Community banner: {archive}")
    old=src[start:end]
    rows={}
    for position,row in enumerate(ARTICLE.findall(old)):
        found=HREF.search(row)
        if not found:raise RuntimeError(f"Archive contains an invalid card: {archive}")
        url=unescape(found.group(1))
        # An edited YouTube post moving sections must never appear in both.
        if url in routes and routes[url]!=category:continue
        m=DATE.search(row)
        ts=instant(unescape(m.group(1))) if m else 0.0
        rows[url]=(ts,position,row)
    for ts,url,row in additions:
        rows[url]=(ts,-1,row)
    if len(rows)>1800:
        raise RuntimeError(f"Too many special archive rows: {archive}")
    sorted_rows=sorted(rows.items(),key=lambda item:(item[1][0],-item[1][1],item[0]),reverse=True)
    replacement="\n"+"\n".join(record[2] for _,record in sorted_rows)+"\n"
    output=src[:start]+replacement+src[end:]
    return file,output,(len(additions),len(sorted_rows))

def sync(root:Path=ROOT):
    items,routes=community_rows(root)
    staged=[]
    for name,(category,archive) in SECTIONS.items():
        staged.append(merge_category(root,category,archive,items[category],routes))
    for file,text,_ in staged:
        if file.read_text(encoding="utf-8")!=text:
            file.write_text(text,encoding="utf-8")
            print(f"UPDATED {file.name}: Community special articles included")
    return {category:row[2] for (_, (category,_)),row in zip(SECTIONS.items(),staged)}

if __name__=="__main__":
    try:
        summary=sync()
        print("PASS: Community Tech Impact / Gaming Inside publication routing",summary)
    except (OSError,ValueError,RuntimeError) as exc:
        print("ERROR: special Community archive merge blocked: "+str(exc),file=sys.stderr)
        raise SystemExit(1)
