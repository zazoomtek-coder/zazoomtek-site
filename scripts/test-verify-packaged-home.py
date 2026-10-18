#!/usr/bin/env python3
"""Synthetic regression tests for the exact Cloudflare build output guard."""
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
spec=importlib.util.spec_from_file_location("packaged",Path(__file__).with_name("verify-packaged-home.py"))
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
def main():
    with TemporaryDirectory() as folder:
        root=Path(folder)
        items=[]
        cards=[]
        for n in range(5):
            section="gaming" if n==4 else "tech"
            link=f"/news-verified-{n}.html"
            img=f"https://images.example.com/photo{n}.jpg"
            title=f"Pubblicazione originale ZazoomTek test numero {n}"
            items.append({"section":section,"url":link,"image":img,"title":title,
                          "published_date":"2026-01-01"})
            (root/link[1:]).write_text("verified",encoding="utf-8")
            cards.append(f'<a title="{title}" data-feature-section="{section}" href="{link}" aria-label="{title}" class="zt-feature-card"><img src="{img}"></a>')
        marks=mod.MARKERS
        fragment="<!-- FEATURED_NEWS_START -->"+''.join(cards)+"<!-- FEATURED_NEWS_END -->"
        reviews='<!-- HOME_LATEST_REVIEWS_MAIN_START --><article class="video-card zt-review-card"></article><!-- HOME_LATEST_REVIEWS_MAIN_END -->'
        home="<html>"+fragment+'<!-- ARTICLE_FEED_START --><!-- ARTICLE_FEED_END -->'+reviews+"</html>"
        (root/"index.html").write_text(home,encoding="utf-8")
        for asset in ("zt-home-live.js","zt-home-graphic-layout-20261016.js","zt-home-graphic-layout-20261016.css"):
            (root/asset).write_text("approved",encoding="utf-8")
        def save(entries):(root/"featured-carousel.json").write_text(json.dumps({"items":entries}),encoding="utf-8")
        save(items)
        assert mod.errors_for(root)==[],mod.errors_for(root)
        save(items[:1]);assert mod.errors_for(root)
        save(items)
        (root/"index.html").write_text(home.replace("zt-feature-card","not-featured",1),encoding="utf-8")
        assert mod.errors_for(root)
        (root/"index.html").write_text(home,encoding="utf-8")
        fake=[dict(x) for x in items];fake[0]["url"]=fake[1]["url"];save(fake)
        assert mod.errors_for(root)
        fake=[dict(x) for x in items];fake[0]["published_date"]="2099-01-01";save(fake)
        assert mod.errors_for(root)
        save(items)
        assert mod.errors_for(root)==[],mod.errors_for(root)
    print("PASS: valid, stale dates preserved, missing cards, duplicated URLs and future dates rejected")
if __name__=="__main__":main()
