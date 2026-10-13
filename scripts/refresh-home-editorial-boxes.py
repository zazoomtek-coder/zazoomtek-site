#!/usr/bin/env python3
"""Refresh Home editorial cards from articles actually published by ZazoomTek.

No AI drafting, no fabricated news, no metric-free "most read" ranking.
Daily rotation takes place only among real, link-checked published articles.
The original three-column design, reviews, YouTube widgets and import markers
are not changed. Idempotent within the same day when sources do not change.
"""
from __future__ import annotations
import argparse
import datetime as dt
import html
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
ITALY = ZoneInfo("Europe/Rome")
ARTICLE_RE = re.compile(r'<article class="(?:news-row|article-row)"[^>]*>.*?</article>', re.S)
H2_RE = re.compile(r'<h2[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>\s*</h2>', re.S)
H3_RE = re.compile(r'<h3[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>\s*</h3>', re.S)
IMAGE_RE = re.compile(r'<img\b[^>]*\bsrc="([^"]+)"[^>]*>', re.S)
META_RE = re.compile(r'(?:news-meta|article-meta)"[^>]*>(.*?)</div>', re.S)
STRIP_TAGS = re.compile(r'<[^>]*>')
CATEGORIES = ("tech", "gaming")

def readable(raw: str) -> str:
    return " ".join(html.unescape(STRIP_TAGS.sub(" ", raw)).split())

def clean_url(value: str) -> str | None:
    value = html.unescape(value.strip())
    if not value or value.startswith(("#", "javascript:", "//")):
        return None
    url = urlsplit(value)
    if url.scheme and url.scheme not in ("http", "https"):
        return None
    if url.netloc and url.netloc.lower() not in ("zazoomtek.it", "www.zazoomtek.it"):
        return None
    path = url.path.lstrip("/")
    if not re.fullmatch(r"[A-Za-z0-9._-]+\.html", path):
        return None
    if not (ROOT / path).is_file():
        return None
    return "/" + path

def valid_image(value: str) -> bool:
    value = html.unescape(value.strip())
    if value.startswith("https://"):
        return bool(urlsplit(value).netloc)
    if value.startswith("/") and not value.startswith("//"):
        asset = (ROOT / value.lstrip("/")).resolve()
        return asset.is_relative_to(ROOT) and asset.is_file()
    return False

def extract(page: str) -> list[dict]:
    text = (ROOT / page).read_text(encoding="utf-8")
    output: list[dict] = []
    seen: set[str] = set()
    for chunk in ARTICLE_RE.findall(text):
        link = H2_RE.search(chunk) or H3_RE.search(chunk)
        image = IMAGE_RE.search(chunk)
        if not link or not image:
            continue
        href, title = clean_url(link.group(1)), readable(link.group(2))
        photo = html.unescape(image.group(1))
        if not href or not title or not valid_image(photo) or href in seen:
            continue
        seen.add(href)
        meta = META_RE.search(chunk)
        date = readable(meta.group(1)) if meta else ""
        output.append({"url": href, "title": title, "image": photo, "date": date})
    return output

def home_urls(source: str) -> set[str]:
    if source.count("<!-- ARTICLE_FEED_START -->") != 1 or source.count("<!-- ARTICLE_FEED_END -->") != 1:
        raise RuntimeError("Home canonical news markers missing or duplicated")
    feed = source.split("<!-- ARTICLE_FEED_START -->", 1)[1].split("<!-- ARTICLE_FEED_END -->", 1)[0]
    urls = set()
    for row in ARTICLE_RE.findall(feed):
        link = H3_RE.search(row)
        if link:
            href = clean_url(link.group(1))
            if href:
                urls.add(href)
    if len(urls) != 15:
        raise RuntimeError(f"Expected 15 canonical unique Home news; found {len(urls)}")
    return urls

def distinct(items: list[dict], avoid: set[str]) -> list[dict]:
    result: list[dict] = []
    used = set(avoid)
    for item in items:
        if item["url"] in used:
            continue
        used.add(item["url"])
        result.append(item)
    return result

def choose(items: list[dict], count: int, today: dt.date, keep_latest: int = 2) -> list[dict]:
    """Always show fresh first; rotate the rest once per Rome calendar day."""
    if len(items) < count:
        raise RuntimeError(f"Insufficient distinct published content: need {count}, have {len(items)}")
    fixed = items[:min(keep_latest, count)]
    pool = items[len(fixed):min(len(items), 20)]
    count_rest = count - len(fixed)
    if count_rest <= 0:
        return fixed
    # Stable per day, changing the selection without misrepresenting publication dates.
    offset = today.toordinal() % max(1, len(pool))
    rotated = pool[offset:] + pool[:offset]
    return fixed + rotated[:count_rest]

def esc(value: str) -> str:
    return html.escape(value, quote=True)

def popular_cards(items: list[dict]) -> str:
    out = []
    for item in items:
        title = esc(item["title"])
        prefix = item["url"].lower()
        category = ("GAMING" if any(x in prefix for x in ("gaming", "game", "ps5", "xbox", "nintendo"))
                    else "TECNOLOGIA")
        out.append(
            f'<a class="zt-popular-article" href="{esc(item["url"])}" title="{title}">\n'
            f'  <img src="{esc(item["image"])}" alt="{title}" loading="lazy" decoding="async">\n'
            f'  <span class="zt-popular-copy"><span class="zt-popular-category">{category}</span>'
            f'<strong>{title}</strong></span>\n</a>')
    return "\n".join(out)

def special_cards(items: list[dict]) -> str:
    return "\n".join(
        f'<article class="zt-special-item"><a href="{esc(item["url"])}" class="zt-special-thumb" '
        f'aria-label="{esc(item["title"])}"><img src="{esc(item["image"])}" alt="{esc(item["title"])}" '
        f'loading="lazy"></a><h3><a href="{esc(item["url"])}">{esc(item["title"])}</a></h3></article>'
        for item in items
    )

def replace_once(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, n = re.subn(pattern, lambda _match: replacement, text, count=1, flags=re.S)
    if n != 1:
        raise RuntimeError(f"{label}: missing guarded replacement")
    return updated

def build(today: dt.date) -> tuple[str, str, dict]:
    homepage = (ROOT / "index.html").read_text(encoding="utf-8")
    javascript = (ROOT / "zt-home-live.js").read_text(encoding="utf-8")
    if "ztp-final-balanced-live-20261013" not in homepage:
        raise RuntimeError("Approved Home layout missing; refusing editorial overwrite")
    published_home = home_urls(homepage)
    ordinary = []
    for file in ("news.html", "pagina-2.html", "pagina-3.html", "pagina-4.html"):
        ordinary.extend(extract(file))
    ordinary = distinct(ordinary, published_home)
    if len(ordinary) < 12:
        raise RuntimeError("Too few independent published news for editorial freshness")
    # Prioritize each source's freshest published, category-correct stories.
    # Cross-section exclusion must happen BEFORE selection, not after it.
    tech = choose(distinct(extract("tech-today.html"), published_home), 4, today)
    special_urls = {item["url"] for item in tech}
    gaming = choose(distinct(extract("gaming-today.html"), published_home | special_urls), 4, today)
    special_urls.update(item["url"] for item in gaming)
    ordinary = distinct(ordinary, published_home | special_urls)
    suggested = choose(ordinary, 6, today)
    selected = {item["url"] for item in suggested}
    left = distinct(ordinary, published_home | special_urls | selected)
    editorial = choose(left, 6, today, keep_latest=2)
    if len(set(item["url"] for item in tech + gaming + suggested + editorial)) != 20:
        raise RuntimeError("Editorial box duplicate detected")

    homepage = replace_once(
        homepage,
        r'(?<=<!-- POPULAR_NEWS_ITEMS_START -->).*?(?=<!-- POPULAR_NEWS_ITEMS_END -->)',
        "\n" + popular_cards(suggested) + "\n        ",
        "fresh selected-articles block",
    )
    # A section based on real editorial choice is NOT a measured page-view leaderboard.
    homepage = replace_once(
        homepage,
        r'<div class="zt-popular-head">.*?</div>',
        '<div class="zt-popular-head"><h2 id="zt-popular-title">DA NON PERDERE</h2></div>',
        "honest sidebar heading",
    )
    for section, chosen in (("tech", tech), ("gaming", gaming)):
        homepage = replace_once(
            homepage,
            r'(?<=<div class="zt-special-list" id="zt-special-' + section
            + r'">).*?(?=</div>\s*<div class="zt-special-footer">)',
            "\n" + special_cards(chosen) + "\n          ",
            f"{section} editorial source",
        )
    serialized = json.dumps(
        [{"title":item["title"], "url":item["url"], "image":item["image"]} for item in editorial],
        ensure_ascii=False, separators=(",", ":"),
    ).replace("<", "\\u003c")
    javascript = replace_once(
        javascript, r'const sidebarEditorials=\[.*?\];(?=\s*const editorialBox=)',
        "const sidebarEditorials=" + serialized + ";", "Dalla redazione source",
    )
    # Post conditions defend the Home, and all three original editorial regions.
    if homepage.count("<!-- ARTICLE_FEED_START -->") != 1 or homepage.count("<!-- ARTICLE_FEED_END -->") != 1:
        raise RuntimeError("Article import markers unexpectedly changed")
    if homepage.count("<!-- HOME_GUIDES_INSET_START -->") != 1 or homepage.count("<!-- FEATURED_NEWS_START -->") != 1:
        raise RuntimeError("Reviews/guides/featured layout markers changed")
    if homepage.count('id="zt-special-tech"') != 1 or homepage.count('id="zt-special-gaming"') != 1:
        raise RuntimeError("Editorial boxes missing")
    if homepage.count('<h2 id="zt-popular-title">DA NON PERDERE</h2>') != 1:
        raise RuntimeError("DA NON PERDERE: expected one proper H2 label")
    if re.search(r'\\g<[12]>', homepage):
        raise RuntimeError("Found literal regex back-reference in published HTML")
    report = {"date_italy": today.isoformat(), "suggested": [x["url"] for x in suggested],
              "tech_impact": [x["url"] for x in tech],
              "gaming_inside": [x["url"] for x in gaming],
              "dalla_redazione": [x["url"] for x in editorial]}
    return homepage, javascript, report

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    opts = parser.parse_args()
    date = dt.datetime.now(ITALY).date()
    index, javascript, report = build(date)
    if opts.self_test:
        a, b, _ = build(date)
        assert a == index and b == javascript, "Refresh must be deterministic and idempotent"
        assert sum(len(report[key]) for key in ("suggested", "tech_impact", "gaming_inside", "dalla_redazione")) == 20
        print("PASS: every refreshed card uses a real existing ZazoomTek article + validated thumbnail")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not opts.self_test and not opts.dry_run:
        (ROOT / "index.html").write_text(index, encoding="utf-8")
        (ROOT / "zt-home-live.js").write_text(javascript, encoding="utf-8")

if __name__ == "__main__":
    main()
