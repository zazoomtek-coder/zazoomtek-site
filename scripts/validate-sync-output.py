#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

ROOT=Path(".")

def fail(msg):
    raise SystemExit("VALIDATION ERROR: "+msg)

def load_json_list(path,minimum):
    p=ROOT/path
    if not p.exists():
        fail(f"{path} missing")
    try:
        data=json.loads(p.read_text(encoding="utf-8"))
    except Exception as err:
        fail(f"{path} invalid JSON: {err}")
    if not isinstance(data,list) or len(data)<minimum:
        size=len(data) if isinstance(data,list) else "non-list"
        fail(f"{path} has only {size} items")
    return data

def validate_html_file(path,min_size=1000):
    p=ROOT/path
    if not p.exists():
        fail(f"{path} missing")
    text=p.read_text(encoding="utf-8",errors="replace")
    if len(text)<min_size:
        fail(f"{path} suspiciously small ({len(text)} bytes)")
    low=text.lower()
    if "<html" not in low or "</html>" not in low:
        fail(f"{path} is not a complete HTML document")
    return text

def validate_common():
    index=validate_html_file("index.html",12000)
    for marker in (
        "FEATURED_NEWS_START",
        "ARTICLE_FEED_START",
        "HOME_LATEST_REVIEWS_MAIN_START",
        "SIDEBAR_STACK_VIDEOS_START",
    ):
        if marker not in index:
            fail(f"index.html missing marker {marker}")
    for p in ROOT.glob("*.html"):
        if p.stat().st_size==0:
            fail(f"zero-byte HTML file: {p.name}")
    return index

def validate_community():
    index=validate_common()
    posts=load_json_list(".youtube-posts.json",20)
    ids=[p.get("id") for p in posts if isinstance(p,dict)]
    if len(ids)!=len(posts) or len(set(ids))!=len(ids):
        fail("Community state has missing or duplicate post IDs")
    news=[p for p in posts if str(p.get("text","")).lstrip().lower().startswith("news")]
    reviews=[
        p for p in posts
        if (
            "recensione" in str(p.get("text","")).lower()
            or "voto finale" in str(p.get("text","")).lower()
            or str(p.get("text","")).lstrip().lower().startswith("review")
        )
    ]
    if len(news)<10:
        fail(f"too few Community news items ({len(news)})")
    if len(reviews)<1:
        fail("no Community reviews found")
    validate_html_file("news.html",5000)
    validate_html_file("recensioni-scritte.html",3000)
    if "<!-- FEATURED_NEWS_START -->" not in index:
        fail("featured news block missing")
    print(f"Community validation OK: {len(posts)} posts, {len(news)} news, {len(reviews)} review-like posts")

def validate_videos():
    index=validate_common()
    videos=load_json_list(".youtube-latest.json",20)
    ids=[v.get("id") for v in videos if isinstance(v,dict)]
    if len(ids)!=len(videos) or len(set(ids))!=len(ids):
        fail("video state has missing or duplicate IDs")
    newest=ids[0]
    if newest not in index:
        fail("newest YouTube upload is not referenced by index build state")
    for page in ("gaming.html","recensioni.html","test.html","unboxing.html"):
        validate_html_file(page,2500)
    m=re.search(
        r"<!-- SIDEBAR_STACK_VIDEOS_START -->(.*?)<!-- SIDEBAR_STACK_VIDEOS_END -->",
        index,re.S
    )
    if not m:
        fail("latest-video sidebar block missing")
    cats=re.findall(r'data-category="([^"]+)"',m.group(1))
    if len(cats)!=len(set(cats)):
        fail("duplicate categories in latest-video sidebar")
    if len(cats)>5:
        fail(f"too many sidebar category cards ({len(cats)})")
    print(f"Video validation OK: {len(videos)} uploads, sidebar categories: {', '.join(cats) or 'none'}")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("mode",choices=("community","videos"))
    args=ap.parse_args()
    if args.mode=="community":
        validate_community()
    else:
        validate_videos()

if __name__=="__main__":
    main()
