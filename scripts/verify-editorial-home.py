#!/usr/bin/env python3
"""Fail-closed editorial regression checks before Cloudflare Pages publishing.

This protects the public build from old carousel quotas, disappeared reviews,
missing news categories and accidental duplicate article links. Runs offline.
"""
from __future__ import annotations
from collections import Counter
from datetime import date, datetime, timedelta
from html import unescape
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
THERMO = "thermomate-2500w-recensione-riscaldatore-infrarossi-2-in-1.html"

def read(path: str) -> str:
    file = ROOT / path
    if not file.is_file():
        raise RuntimeError("Required published file missing: " + path)
    return file.read_text(encoding="utf-8")

def check() -> None:
    home = read("index.html")
    archive = read("recensioni-scritte.html")
    js = read("zt-home-live.js")
    manifest = json.loads(read("featured-carousel.json"))
    items = manifest.get("items", [])
    if not isinstance(items, list) or len(items) != 5:
        raise RuntimeError("Featured must always contain exactly 5 real articles")
    urls = [a.get("url", "") for a in items]
    sections = Counter(a.get("section") for a in items)
    if len(set(urls)) != len(urls) or sections.get("tech", 0) > 4 or sections.get("gaming", 0) > 1:
        raise RuntimeError("Featured 4 Tech + 1 Gaming quota or uniqueness violation")
    if any(a.get("section") not in ("tech","gaming") for a in items):
        raise RuntimeError("Tech Impact/Gaming Inside leaked into ordinary carousel")
    if [a["section"] for a in items]!=["tech"]*4+["gaming"]:
        raise RuntimeError("Featured: big card must be Tech and bottom-right must be Gaming")
    for row in items:
        url = row["url"]
        if not re.fullmatch(r"/news-[\w-]+\.html", url) or not (ROOT / url[1:]).is_file():
            raise RuntimeError("Missing featured source article: " + url)
        cover = row.get("image", "")
        if not cover.startswith(("https://", "/assets/")):
            raise RuntimeError("Missing or invalid featured image: " + url)
        if cover.startswith("/") and not (ROOT / cover.lstrip("/")).is_file():
            raise RuntimeError("Missing local featured image: " + cover)
    start = home.find("<!-- FEATURED_NEWS_START -->")
    end = home.find("<!-- FEATURED_NEWS_END -->", start)
    if start < 0 or end < start:
        raise RuntimeError("Home featured markers absent")
    featured = home[start:end]
    if featured.count('data-feature-section="tech"') != sections.get("tech", 0):
        raise RuntimeError("Server-rendered Tech carousel differs from manifest")
    if featured.count('data-feature-section="gaming"') != sections.get("gaming", 0):
        raise RuntimeError("Server-rendered Gaming carousel differs from manifest")
    rendered_categories=re.findall(r'data-feature-section="(tech|gaming)"',featured)
    if len(rendered_categories)==5 and rendered_categories!=["tech"]*4+["gaming"]:
        raise RuntimeError("Home featured lead or bottom-right Gaming slot changed")
    if "function chooseFive(items)" not in home or "tech.length===4 && gaming.length===1" not in home:
        raise RuntimeError("Client carousel fallback no longer enforces four Tech and one Gaming")
    layout_js=read("zt-home-graphic-layout-20261016.js")
    layout_css=read("zt-home-graphic-layout-20261016.css")
    if 'const chosen=tech.concat(gaming)' not in layout_js:
        raise RuntimeError("Frontend must enforce Tech first and Gaming last")
    if 'data-feature-section="gaming"]:last-child' not in layout_css:
        raise RuntimeError("Grid must reserve bottom-right location for Gaming")
    # A story belongs to the featured carousel OR to its Tech/Gaming column,
    # never both. Old stories return at their ORIGINAL timestamp when replaced.
    if ('featuredOnHome.has(articlePath)' not in js
            or 'const featured=featuredPaths();' not in js
            or '!featured.has(url)' not in js
            or 'sourcePublishedAt(row)' not in js
            or 'b.time-a.time' not in js
            or 'column.replaceChildren(...ranked.slice(0,10)' not in js
            or 'MutationObserver(paintCurrentColumns)' not in js
            or 'data-published-at' not in read("scripts/update-youtube-posts.py")):
        raise RuntimeError("Featured/column exclusivity or original timestamps are missing")
    for path in ("/news.html","/news-2.html","/news-3.html","/news-4.html","/news-5.html"):
        if path not in js:
            raise RuntimeError("Home lacks archive pagination: " + path)
    if 'cache:"no-store"' not in js:
        raise RuntimeError("Home archive is allowed to serve obsolete cached news")
    # There are enough genuine classified Tech stories in the public archive
    # to fill the column with ten distinct links. Do not silently show only six.
    seen = {"tech": set(), "gaming": set()}
    for n in range(1, 6):
        name = "news.html" if n == 1 else f"news-{n}.html"
        if not (ROOT / name).is_file():
            continue
        page = read(name)
        for block in re.findall(r'<article class="news-row"[^>]*>.*?</article>',page,re.S):
            signature = re.search(r'data-news-search="([^"]*)"',block)
            link = re.search(r'<h2>\s*<a\s+href="([^"]+)"',block)
            if not signature or not link:
                continue
            mark = re.search(r'\bnews\s+(tech|gaming)\s*:',unescape(signature.group(1)),re.I)
            if mark:
                seen[mark.group(1).lower()].add(link.group(1))
    if len(seen["tech"]) < 10 or len(seen["gaming"]) < 10:
        raise RuntimeError("Not enough verified Tech/Gaming archive cards for two full Home columns")
    # ThermoMate must be the first dated review and first Tech shelf card.
    if not (ROOT / THERMO).is_file():
        raise RuntimeError("ThermoMate article is missing from the repository")
    cover = ROOT / "assets/recensioni/thermomate-2500w/cover.webp"
    if not cover.is_file():
        raise RuntimeError("ThermoMate cover missing")
    reviews = re.findall(r'<article class="news-row"[^>]*>.*?</article>',archive,re.S)
    if not reviews or not any(THERMO in row for row in reviews):
        raise RuntimeError("ThermoMate disappeared from written reviews")
    # Verify that ALL written-review dates are chronologically sorted.
    months = {m:i for i,m in enumerate(
        "gennaio febbraio marzo aprile maggio giugno luglio agosto settembre ottobre novembre dicembre".split(),1)}
    known = []
    for row in reviews:
        m = re.search(r'<div class="news-meta">([^<]*)</div>',row,re.I)
        match = re.search(r'(\d{1,2})\s+('+"|".join(months)+r')\s+(\d{4})',
                          unescape(m.group(1)) if m else "",re.I)
        if match:
            day,month,year = match.groups()
            known.append((int(year),months[month.lower()],int(day)))
    if known != sorted(known,reverse=True):
        raise RuntimeError("Written reviews are out of chronological order")
    if datetime.now(ZoneInfo("Europe/Rome")).date() == date(2026,10,17) and THERMO not in reviews[0]:
        raise RuntimeError("Today's ThermoMate review is not first in written reviews")
    live_reviews = home.split("<!-- HOME_LATEST_REVIEWS_MAIN_START -->",1)[-1].split(
        "<!-- HOME_LATEST_REVIEWS_MAIN_END -->",1)[0]
    if datetime.now(ZoneInfo("Europe/Rome")).date() == date(2026,10,17):
        first = live_reviews.split('<article class="video-card zt-review-card">',2)
        if len(first) < 2 or THERMO not in first[1]:
            raise RuntimeError("Today's ThermoMate not first in Home latest reviews")
    anchor = js.find('track.replaceChildren(',js.find('const gamingCards=olderCards.filter'))
    if anchor < 0 or THERMO not in js[anchor:anchor+800]:
        raise RuntimeError("Tech shelf does not place ThermoMate first")
    if 'fetch("/recensioni-scritte.html",{cache:"no-store"})' not in js:
        raise RuntimeError("Tech reviews are not refreshed automatically")
    # Home recovery: protect the approved two-column Tech + Gaming layout.
    # The post-release dynamic de-duplication/reordering corrupted the visible
    # columns. Keep the stable ten-news-per-column rendering until redesigned
    # and tested against actual browser screenshots.
    if ('ztp-two-news-columns' not in js
            or 'ztp-news-tech' not in js or 'ztp-news-gaming' not in js
            or 'all.slice(10).forEach(function(row){row.remove();})' not in js):
        raise RuntimeError("Stable Tech/Gaming Home columns are missing")
    if 'reservedEditorialPaths()' in js:
        raise RuntimeError("Regressed Home dynamic reordering was reintroduced")
    if ('data-zt-align-fill' not in js
            or 'remaining={tech:reserve("tech"),gaming:reserve("gaming")}' not in js
            or 'new ResizeObserver(requestAlignment)' not in js
            or 'sourcePublishedAt(row)' not in js
            or 'const featured=featuredPaths();' not in js):
        raise RuntimeError("Home must fill columns from unique dated archive articles after lazy image loads")
    if 'ZT_HOME_GAMING_THREE_EXTRA_20261014' in js:
        raise RuntimeError("Old hardcoded Gaming article fillers remain enabled")
    if '20261017stableColumnsRollback4' not in home:
        raise RuntimeError("Home is not loading the stable column layout")
    # Manual Tech reviews must use the complete ZazoomTek editorial template.
    thermo=read(THERMO)
    if ('zt-thermo-full-editorial' not in thermo
            or thermo.count('<section class="side-box') < 10
            or 'zt-mix-recent' not in thermo or 'zt-mix-feature' not in thermo
            or 'zt-amazon-partner' not in thermo or 'zt-sidebar-editorial' not in thermo
            or 'Gaming Inside' not in thermo or 'Tech Impact' not in thermo):
        raise RuntimeError("ThermoMate review is missing complete editorial side boxes")
    print("EDITORIAL PREFLIGHT PASSED: 4 Tech + 1 Gaming, archive pagination, "
          "10+ authentic stories per column, ThermoMate in both Home shelves and review archive")

if __name__ == "__main__":
    check()
