#!/usr/bin/env python3
"""Read-only validator for actual Cloudflare dist; no network or deployment."""
from __future__ import annotations
import argparse
from datetime import date, datetime
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

EXPECTED=["tech","tech","tech","tech","gaming"]
MARKERS=["FEATURED_NEWS_START","FEATURED_NEWS_END","ARTICLE_FEED_START",
         "ARTICLE_FEED_END","HOME_LATEST_REVIEWS_MAIN_START","HOME_LATEST_REVIEWS_MAIN_END"]

class Cards(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.cards=[]
        self.active=None
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="a" and "zt-feature-card" in (a.get("class") or "").split():
            self.active={"section":a.get("data-feature-section"),"url":a.get("href"),
                         "title":a.get("title"),"label":a.get("aria-label"),"image":None}
            self.cards.append(self.active)
        elif tag=="img" and self.active is not None:
            self.active["image"]=a.get("src")
    def handle_endtag(self,tag):
        if tag=="a":self.active=None

def errors_for(root:Path):
    bad=[]
    def fail(message):bad.append(message)
    home_path=root/"index.html"
    manifest_path=root/"featured-carousel.json"
    if not home_path.is_file() or not manifest_path.is_file():
        return ["Missing built index.html or featured-carousel.json"]
    home=home_path.read_text(encoding="utf-8")
    try:
        state=json.loads(manifest_path.read_text(encoding="utf-8"))
        items=state["items"]
        if not isinstance(items,list):raise TypeError("Not an array")
    except (ValueError,TypeError,KeyError) as exc:
        return ["Featured manifest malformed: "+str(exc)]
    if len(items)!=5:fail("Exactly five featured news required")
    if any(not isinstance(i,dict) for i in items):return bad+["Invalid featured article object"]
    if [i.get("section") for i in items]!=EXPECTED:fail("Manifest categories/order not 4 Tech + 1 Gaming")
    urls=[i.get("url") for i in items]
    if any(not isinstance(u,str) for u in urls) or len(set(urls))!=5:
        fail("Missing or duplicate featured links")
    today=datetime.now(ZoneInfo("Europe/Rome")).date()
    for n,item in enumerate(items,1):
        url=item.get("url")
        image=item.get("image")
        title=item.get("title")
        if not isinstance(title,str) or len(title.strip())<12:fail(f"Card {n}: missing title")
        if not isinstance(url,str) or not re.fullmatch(r"/news-[A-Za-z0-9_-]+\.html",url):
            fail(f"Card {n}: invalid article link")
        elif not (root/url[1:]).is_file():fail(f"Card {n}: missing published article")
        if not isinstance(image,str) or not image.startswith(("https://","/assets/")):
            fail(f"Card {n}: invalid image")
        elif image.startswith("/assets/") and not (root/image[1:]).is_file():
            fail(f"Card {n}: missing local image")
        try:
            day=date.fromisoformat(item["published_date"])
            if day>today:fail(f"Card {n}: date in future")
        except (TypeError,ValueError,KeyError):
            fail(f"Card {n}: invalid date")
    if any(home.count("<!-- "+m+" -->")!=1 for m in MARKERS):
        fail("Home structural boundary missing/duplicated")
        return bad
    snippet=home.split("<!-- FEATURED_NEWS_START -->",1)[1].split("<!-- FEATURED_NEWS_END -->",1)[0]
    parser=Cards();parser.feed(snippet)
    if len(parser.cards)!=5:fail(f"Home has {len(parser.cards)} cards, not five")
    if [c["section"] for c in parser.cards]!=EXPECTED:fail("Home sections/order mismatch")
    if [c["url"] for c in parser.cards]!=urls:fail("Home featured links mismatch manifest")
    if [c["image"] for c in parser.cards]!=[i.get("image") for i in items]:
        fail("Home featured images mismatch manifest")
    if any(not c["title"] or not c["label"] for c in parser.cards):
        fail("Home featured labels missing")
    # Home script asset references are validated by verify-home-layout-lock.py,
    # now an integrity-only guard. Legacy file names are not a design contract.
    # The visual "Recensioni Tech" heading is rendered client-side; check the
    # actual server-rendered review cards, not a label absent from source HTML.
    reviews=home.split("<!-- HOME_LATEST_REVIEWS_MAIN_START -->",1)[1].split(
        "<!-- HOME_LATEST_REVIEWS_MAIN_END -->",1)[0]
    if '<article class="video-card zt-review-card">' not in reviews:
        fail("Latest written review cards missing from built Home")
    return bad

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,default=Path("dist"))
    args=p.parse_args()
    bad=errors_for(args.root)
    if bad:raise SystemExit("BLOCK DEPLOY: "+"; ".join(bad))
    print("PASS: packaged Home matches all five real featured news, images, order and valid public content")

if __name__=="__main__":main()
