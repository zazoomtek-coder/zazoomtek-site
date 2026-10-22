#!/usr/bin/env python3
"""Prevent Home LCP and CLS regressions without changing editorial design.

This test exercises the SAME featured builder as the Cloudflare deployment,
including changing headlines/covers after a new approved YouTube import.
"""
from __future__ import annotations
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import re

ROOT = Path(__file__).resolve().parents[1]
SPEC = spec_from_file_location("zt_featured_perf", ROOT / "scripts/cloudflare-sync-featured-home.py")
assert SPEC is not None and SPEC.loader is not None
mod = module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def check_repo_source():
    source = (ROOT / "index.html").read_text(encoding="utf-8")
    head = source.split("</head>", 1)[0]
    assert head.count('id="zt-home-graphic-approved-20261016"') == 1, (
        "Home CSS must load in document head, not wait for DOMContentLoaded")
    assert re.search(r"/zt-home-graphic-layout-20261016\\.css\\?v=[A-Za-z0-9_-]+", head), "Approved Home CSS missing"
    assert "if(unchanged)return;" in source, (
        "Do not refetch/replace already decoded featured hero images")
    assert "if(i===0)img.fetchPriority='high'" in source


def check_builder():
    with TemporaryDirectory(prefix="zt-perf-test-") as temp:
        root = Path(temp)
        source = ('<!DOCTYPE html><html><head><meta name="viewport" '
                  'content="width=device-width,initial-scale=1">'
                  '<title>News</title></head><body>'
                  + mod.START + '<div id="ztFeaturedGrid">OLD</div>' + mod.END
                  + '</body></html>')
        (root / "index.html").write_text(source, encoding="utf-8")
        (root / "featured-editorial-pins.json").write_text(
            json.dumps({"items": []}), encoding="utf-8")
        items = [
            {"section": "tech" if i < 4 else "gaming",
             "title": "Verified ZazoomTek editorial news " + str(i),
             "url": f"/news-performance-{i}.html",
             "image": ("https://yt3.ggpht.com/" + "A" * 28
                       + "=s1600-rw-nd-v1") if i == 0
                      else "https://images.example.org/demo-" + str(i) + ".jpg",
             "published_date": "2026-10-20"}
            for i in range(5)
        ]
        for item in items:
            (root / item["url"].lstrip("/")).write_text("<article>test</article>")
        (root / "featured-carousel.json").write_text(
            json.dumps({"items": items}), encoding="utf-8")
        assert mod.sync(root)
        page = (root / "index.html").read_text(encoding="utf-8")
        head = page.split("</head>", 1)[0]
        featured = page.split(mod.START, 1)[1].split(mod.END, 1)[0]
        assert head.count(mod.PRELOAD_START) == 1
        assert head.count(mod.PRELOAD_END) == 1
        assert head.count('rel="preload" as="image"') == 1
        assert 'imagesrcset="' in head and 'imagesizes="' in head
        assert 'fetchpriority="high"' in head
        assert featured.count('fetchpriority="high"') == 1
        assert featured.count('loading="eager"') == 1
        assert featured.count('loading="lazy"') == 4
        assert featured.count('width="1600" height="900"') == 5
        assert 'srcset="' in featured
        assert not mod.sync(root), "Builder must be idempotent"
        # A YouTube/news import changes the cover: stale preload must be replaced.
        old_image = items[0]["image"]
        items[0]["image"] = "https://yt3.ggpht.com/" + "B" * 28 + "=s1600-rw-nd-v1"
        (root / "featured-carousel.json").write_text(
            json.dumps({"items": items}), encoding="utf-8")
        assert mod.sync(root)
        current = (root / "index.html").read_text(encoding="utf-8")
        current_head = current.split("</head>", 1)[0]
        assert items[0]["image"] in current_head
        assert old_image not in current_head
        assert current_head.count(mod.PRELOAD_START) == 1
        assert not mod.sync(root)
    print("PASS: first paint CSS, fast LCP preload, responsive hero, stable slots and correct YouTube image refresh")


if __name__ == "__main__":
    check_repo_source()
    check_builder()
