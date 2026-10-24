#!/usr/bin/env python3
"""Independent Home highlights: four newest published Tech + one Gaming.

Only replaces FEATURED_NEWS markup and its JSON data file; all other
layout/CSS and the imported articles remain untouched.
"""
from __future__ import annotations
import html
import json
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from editorial_workday import editorial_order, edition, FALLBACK

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
            if not (category and link):continue
            url=html.unescape(link.group(1))
            if not url.startswith("/"):url="/"+url
            title=html.unescape(re.sub(r'<[^>]+>','',link.group(2))).strip()
            cover=html.unescape(image.group(1)) if image else FALLBACK
            if not title or not url:continue
            found.append({"section":category.group(1).lower(),"url":url,
                "title":title,"image":cover,
                "published_date":date.group(1)[:10] if date else ""})
        except (AttributeError,ValueError,TypeError):
            continue
    return found

def deduplicate_stories(stories:list[dict])->list[dict]:
    """Keep unique real URLs; allow same-title posts with different IDs."""
    found=[];seen=set()
    for row in sorted(stories,key=lambda r:r.get("published_date") or "",reverse=True):
        url=str(row.get("url") or "").split("?",1)[0].lower()
        if not url or url in seen or not row.get("title"):continue
        seen.add(url);found.append(row)
    return found

def select(current:list[dict],older:list[dict])->list[dict]:
    """One workday and daily rotation; never leave editorial box empty."""
    pool=deduplicate_stories(current)
    dated=[{**row,"published":row.get("published_date") or ""} for row in pool]
    selection=[];seen=set()
    for category,max_items in (("tech",4),("gaming",1)):
        ranked=editorial_order([x for x in dated if x["section"]==category],
                               group=category,page="featured")
        for row in ranked[:max_items]:
            if row["url"] not in seen:selection.append(row);seen.add(row["url"])
    for row in editorial_order(dated,group="news",page="featured-fill"):
        if len(selection)>=5:break
        if row["url"] not in seen:selection.append(row);seen.add(row["url"])
    return selection


def render(selected: list[dict]) -> str:
    anchors=[]
    for index,item in enumerate(selected):
        label=html.escape(item["title"],quote=True)
        href=html.escape(item["url"],quote=True)
        cover=html.escape(item.get("image") or FALLBACK,quote=True)
        anchors.append('<a class="zt-feature-card zt-feature-small zt-home-editorial-card" data-feature-section="'
            +html.escape(item["section"])+'" href="'+href+'" title="'+label+
            '" aria-label="'+label+'"><img src="'+cover+'" alt="'+label+
            '" loading="'+("eager" if index==0 else "lazy")+
            '" decoding="async" onerror="this.onerror=null;this.src=\''+FALLBACK+
            '\'"><span class="zt-home-editorial-label">'+label+'</span></a>')
    return ('<div class="zt-featured-grid zt-home-primary-editorials" id="ztFeaturedGrid" '+
        'data-editorial-edition="'+edition()["edition_day"]+'" '
        'aria-label="Quattro news Tech e una news Gaming in evidenza">'
        +''.join(anchors)+'</div>')

def update(root: Path = ROOT) -> int:
    home=root/"index.html"
    feed=root/"news.html"
    manifest=root/"featured-carousel.json"
    if not home.is_file() or not feed.is_file():return 0
    current=candidates(feed.read_text(encoding="utf-8"))
    selected=select(current,[])
    # Prefer todays news and refill from latest dates without faking their age.
    original=home.read_text(encoding="utf-8")
    if original.count(START)!=1 or original.count(END)!=1:return 0
    start=original.index(START)+len(START)
    end=original.index(END,start)
    published=original[:start]+"\n"+render(selected)+"\n"+original[end:]
    if published!=original:home.write_text(published,encoding="utf-8")
    payload={**edition(),"items":selected}
    manifest.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",
                        encoding="utf-8")
    print("Featured: workday synchronized editorial boxes:",len(selected))
    return len(selected)

if __name__=="__main__":
    update()
