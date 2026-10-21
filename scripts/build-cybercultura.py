#!/usr/bin/env python3
"""Assemble Cybercultura from BOTH existing, already-published category archives.

Legacy Tech Impact and Gaming Inside URLs are retained as stable compatibility
sources. All articles remain at their original URLs; the new section presents
the combined verified items and the sitewide menu exposes only Cybercultura.
Runs only at build time, after both YouTube Community and approved special
publishers have updated their independent original category archives.
"""
from __future__ import annotations
from html import escape, unescape
from pathlib import Path
from datetime import date
import re

ROOT=Path(__file__).resolve().parents[1]
START="<!-- ZT_CYBERCULTURA_ITEMS_START -->"
END="<!-- ZT_CYBERCULTURA_ITEMS_END -->"
INPUTS=(("Tech Impact","tech-today.html","tech-impact"),
        ("Gaming Inside","gaming-today.html","gaming-inside"))
LIST_OPEN=re.compile(r'<div\s+class="news-list"\s+id="newsList"\s+data-auto-articles="(tech|gaming)">',re.I)
ROW=re.compile(r'<article\b[^>]*\bclass="[^"]*\bnews-row\b[^"]*"[^>]*>[\s\S]*?</article>',re.I)
URL=re.compile(r'<h2\b[^>]*>\s*<a\b[^>]*href="(/[^"]+\.html)"',re.I)
DATE=re.compile(r'<div\b[^>]*class="news-meta"[^>]*>\s*[^<]*?(\d{4}-\d{2}-\d{2})',re.I)


def read_archive(root:Path, section:str, filename:str, slug:str) -> list[tuple[str,str,str,str]]:
    source=(root/filename).read_text(encoding="utf-8")
    head=LIST_OPEN.search(source)
    if not head or head.group(1)!=("tech" if section=="Tech Impact" else "gaming"):
        raise RuntimeError("Approved category archive missing: "+filename)
    bound=source.find("<!-- ZT_COMMUNITY_BANNER_START -->",head.end())
    if bound<0:
        bound=source.find("</section>",head.end())
    if bound<0:
        raise RuntimeError("Category archive body missing: "+filename)
    rows=ROW.findall(source[head.end():bound])
    if not rows:
        raise RuntimeError("Cannot empty the approved Cybercultura source: "+filename)
    result=[]
    for row in rows:
        href=URL.search(row)
        if not href:
            raise RuntimeError("Published category card has no article URL: "+filename)
        url=unescape(href.group(1))
        if not re.fullmatch(r'/[A-Za-z0-9_.-]+\.html',url):
            raise RuntimeError("Unsafe Cybercultura link: "+url)
        if not (root/url.lstrip("/")).is_file():
            raise RuntimeError("Missing published Cybercultura article: "+url)
        found=DATE.search(row)
        published=found.group(1) if found else "0000-00-00"
        # The category is visible on each card without changing its title,
        # description, original article address, date or thumbnail.
        badge=('<span class="zt-cyber-badge'
               + (' zt-cyber-badge--gaming' if slug=="gaming-inside" else '')
               + '">'+escape(section)+'</span>')
        marker='<div class="news-copy">'
        if row.count(marker)!=1:
            raise RuntimeError("Unrecognized category article layout: "+url)
        row=row.replace(marker,marker+badge,1)
        row=row.replace('<article class="news-row"',
                        '<article class="news-row" data-cyber-section="'+slug+'"',1)
        result.append((published,url,section,row))
    return result


def sync(root:Path=ROOT,check:bool=False) -> tuple[int,int]:
    root=Path(root)
    page=root/"cybercultura.html"
    source=page.read_text(encoding="utf-8")
    if source.count(START)!=1 or source.count(END)!=1:
        raise RuntimeError("Cybercultura template markers missing or duplicated")
    seen=set()
    collected=[]
    counts={}
    for name,filename,slug in INPUTS:
        rows=read_archive(root,name,filename,slug)
        counts[slug]=len(rows)
        for row in rows:
            if row[1] in seen:continue
            seen.add(row[1])
            collected.append(row)
    # News first: same published items, no fabricated content, no duplicates.
    collected.sort(key=lambda item:(item[0],item[1]),reverse=True)
    built="\n".join(row[3] for row in collected)
    a=source.index(START)+len(START)
    b=source.index(END,a)
    updated=source[:a]+"\n"+built+"\n"+source[b:]
    if updated!=source and not check:
        page.write_text(updated,encoding="utf-8")
    print(f"CYBERCULTURA: {len(collected)} unique published news "
          f"(Tech Impact {counts['tech-impact']}, Gaming Inside {counts['gaming-inside']}); "
          +("change needed" if check and updated!=source else
            "synced" if updated!=source else "already synchronized"))
    return len(collected),len(seen)


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--check",action="store_true")
    args=p.parse_args()
    sync(ROOT,args.check)
