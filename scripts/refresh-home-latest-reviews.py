#!/usr/bin/env python3
"""Synchronize Home 'Ultime recensioni' from published reviews without network access.

Canonical sources: approved site reviews in recensioni-scritte.html, plus saved
YouTube Community review posts. Works on every deployment, even when a manual
review page lacks Review JSON-LD/article:published_time metadata. Only the
review-card marker block of index.html is modified.
"""
import argparse
import json
from pathlib import Path
import re
import runpy

ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT/"scripts"/"update-youtube-posts.py"
INDEX=ROOT/"index.html"
ARCHIVE=ROOT/"recensioni-scritte.html"
STATE=ROOT/".youtube-posts.json"
START="<!-- HOME_LATEST_REVIEWS_MAIN_START -->"
END="<!-- HOME_LATEST_REVIEWS_MAIN_END -->"
CARDS=re.compile(r'<article class="video-card zt-review-card">.*?</article>',re.S)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    if not ARCHIVE.is_file() or not STATE.is_file() or not SOURCE.is_file():
        raise SystemExit("Required published review archive, Community state or updater missing")
    engine=runpy.run_path(str(SOURCE),run_name="_zt_refresh_review_engine")
    posts=json.loads(STATE.read_text(encoding="utf-8"))
    if not isinstance(posts,list) or not posts:
        raise SystemExit("No Community post state: refusing to remove approved Home reviews")
    all_pages,_=engine["existing_review_pages"]()
    approved_posts=engine["select_unique_reviews"](posts,all_pages)
    rendered=engine["render_home_latest_reviews"](approved_posts,limit=5)
    cards=CARDS.findall(rendered)
    if len(cards)!=5:
        raise SystemExit(f"Refusing replacement: expected 5 real cards, got {len(cards)}")
    slugs=re.findall(r'<a class="video-thumb zt-review-thumb" href="/([^"]+)"',rendered)
    if len(slugs)!=5 or len(set(slugs))!=5:
        raise SystemExit("Duplicate or malformed review card URLs")
    for slug in slugs:
        if not re.fullmatch(r"[a-zA-Z0-9._-]+\.html",slug) or not (ROOT/slug).is_file():
            raise SystemExit(f"Unpublished or missing linked review {slug}")
    current=INDEX.read_text(encoding="utf-8")
    if current.count(START)!=1 or current.count(END)!=1:
        raise SystemExit("Current homepage review markers are not unique; aborting")
    out=current[:current.index(START)]+rendered+current[current.index(END)+len(END):]
    if '<!-- ARTICLE_FEED_START -->' not in out or '<!-- HOME_GUIDES_INSET_START -->' not in out:
        raise SystemExit("Homepage news or guides marker missing")
    print("Homepage newest 5 reviews:",", ".join(slugs))
    print("Changed:",out!=current)
    if not args.check and out!=current:
        INDEX.write_text(out,encoding="utf-8")

if __name__=="__main__":
    main()
