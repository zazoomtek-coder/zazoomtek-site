#!/usr/bin/env python3
"""Independent Home highlights: four newest published Tech + one Gaming.

Only replaces FEATURED_NEWS markup and its JSON data file; all other
layout/CSS and the imported articles remain untouched.
"""
from __future__ import annotations
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
START="<!-- FEATURED_NEWS_START -->"
END="<!-- FEATURED_NEWS_END -->"

def candidates(document: str) -> list[dict]:
    found=[]
    for article in re.findall(r'<article\b[^>]*class="news-row"[^>]*>[\s\S]*?</article>',document,re.I):
        try:
            category=re.search(r'data-post-category="(tech|gaming)"',article,re.I)
            link=re.search(r'<h2\b[^>]*>\s*<a\b[^>]*href="([^"]+)"[^>]*>([\s\S]*?)</a>',article,re.I)
            image=re.search(r'<img\b[^>]*src="([^"]+)"',article,re.I)
            date=re.search(r'data-published-at="([^"]+)"',article)
            if not (category and link and image):continue
            url=html.unescape(link.group(1))
            if not url.startswith("/"):url="/"+url
            title=html.unescape(re.sub(r'<[^>]+>','',link.group(2))).strip()
            cover=html.unescape(image.group(1))
            if not title or not url or not cover:continue
            found.append({"section":category.group(1).lower(),"url":url,
                "title":title,"image":cover,
                "published_date":date.group(1)[:10] if date else ""})
        except (AttributeError,ValueError,TypeError):
            continue
    return found

def select(current: list[dict], older: list[dict]) -> list[dict]:
    chosen=[];used=set()
    for section,limit in (("tech",4),("gaming",1)):
        count=0
        for story in current+older:
            url=story.get("url") if isinstance(story,dict) else None
            if not isinstance(story,dict) or story.get("section")!=section or not url or url in used:continue
            chosen.append(story);used.add(url);count+=1
            if count==limit:break
    return chosen

def render(selected: list[dict]) -> str:
    anchors=[]
    for index,item in enumerate(selected):
        label=html.escape(item["title"],quote=True)
        href=html.escape(item["url"],quote=True)
        cover=html.escape(item["image"],quote=True)
        anchors.append('<a class="zt-feature-card zt-feature-small" data-feature-section="'
            +html.escape(item["section"])+'" href="'+href+'" title="'+label+
            '" aria-label="'+label+'"><img src="'+cover+'" alt="'+label+
            '" loading="'+("eager" if index==0 else "lazy")+
            '" decoding="async"></a>')
    return ('<div class="zt-featured-grid" id="ztFeaturedGrid" '
        'aria-label="Quattro news Tech e una news Gaming in evidenza">'
        +''.join(anchors)+'</div>')

def update(root: Path = ROOT) -> int:
    home=root/"index.html"
    feed=root/"news.html"
    manifest=root/"featured-carousel.json"
    if not home.is_file() or not feed.is_file():return 0
    current=candidates(feed.read_text(encoding="utf-8"))
    older=[]
    if manifest.is_file():
        try:older=json.loads(manifest.read_text(encoding="utf-8")).get("items",[])
        except (ValueError,AttributeError):pass
    selected=select(current,older)
    if len(selected)!=5:
        # Keep the existing visible box rather than erase it on a sparse feed.
        print("Featured: incomplete source, keeping previous box",len(selected))
        return 0
    original=home.read_text(encoding="utf-8")
    if original.count(START)!=1 or original.count(END)!=1:return 0
    start=original.index(START)+len(START)
    end=original.index(END,start)
    published=original[:start]+"\n"+render(selected)+"\n"+original[end:]
    if published!=original:home.write_text(published,encoding="utf-8")
    payload={"generated_utc":datetime.now(timezone.utc).isoformat(),"items":selected}
    manifest.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",
                        encoding="utf-8")
    print("Featured: 4 Tech and 1 Gaming refreshed")
    return len(selected)

if __name__=="__main__":
    update()
