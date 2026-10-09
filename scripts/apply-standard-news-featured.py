#!/usr/bin/env python3
"""Idempotent post-processing: ten newest photographic NEWS, with daily updates.

Never imports YouTube, never edits review/video pages or special editorial content.
Call after the existing YouTube Community sync, which rewrites the homepage/NEWS.
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
NEWS = ROOT / "news.html"
STANDARD = ROOT / "standard-news.json"
SPECIAL = ROOT / "special-featured.json"
PAGE_START = "<!-- FEATURED_NEWS_START -->"
PAGE_END = "<!-- FEATURED_NEWS_END -->"
FEED_START = "<!-- ARTICLE_FEED_START -->"
FEED_END = "<!-- ARTICLE_FEED_END -->"
STANDARD_START = "<!-- STANDARD_NEWS_ROWS_START -->"
STANDARD_END = "<!-- STANDARD_NEWS_ROWS_END -->"


def esc(v):
    return html.escape(str(v), quote=True)


def load():
    standard = json.loads(STANDARD.read_text(encoding="utf-8")).get("articles", [])
    special = json.loads(SPECIAL.read_text(encoding="utf-8")).get("items", [])
    if len(standard) < 4 or len(special) != 6:
        raise ValueError("Expected four approved standard NEWS and six existing specials.")
    if sum(x.get("kind") == "tech" for x in standard) < 2 or sum(x.get("kind") == "gaming" for x in standard) < 2:
        raise ValueError("Standard NEWS must contain precisely 2 tech + 2 gaming.")
    if sum(x.get("section") == "tech" for x in special) != 4 or sum(x.get("section") == "gaming" for x in special) != 2:
        raise ValueError("The original 4+2 special selection has changed.")
    for x in standard:
        slug = x.get("slug", "")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            raise ValueError("Invalid standard slug")
        page = ROOT / ("news-" + slug + ".html")
        image = ROOT / ("assets/special/news-" + slug + ".webp")
        if not page.is_file() or not image.is_file() or image.stat().st_size > 300000:
            raise RuntimeError("Standard news page / licensed WebP missing: " + slug)
    for x in special:
        slug = x.get("slug", "")
        if not re.fullmatch(r"(?:tech-impact|gaming-inside)-[a-z0-9-]+\.html", slug):
            raise ValueError("Invalid special slug")
        if not (ROOT / slug).is_file():
            raise RuntimeError("Special page missing: " + slug)
    standard.sort(key=lambda x: publication_key(x.get("published_at") or x.get("date")), reverse=True)
    return standard, special


def publication_key(value):
    """Sort by publication date/time, falling back to editorial order on ties."""
    value = str(value or "").strip()
    match = re.match(r"^(\d{4}-\d{2}-\d{2})(?:[T ](\d{2}:\d{2}(?::\d{2})?))?", value)
    if match:
        return match.group(1) + "T" + (match.group(2) or "00:00:00")
    match = re.fullmatch(r"(\d{1,2}) ([a-zà]+) (\d{4})", value.lower())
    months = {"gennaio":1,"febbraio":2,"marzo":3,"aprile":4,"maggio":5,
              "giugno":6,"luglio":7,"agosto":8,"settembre":9,
              "ottobre":10,"novembre":11,"dicembre":12}
    if match and match.group(2) in months:
        return f"{int(match.group(3)):04d}-{months[match.group(2)]:02d}-{int(match.group(1)):02d}T00:00:00"
    return ""


def photo_ready(path):
    if not isinstance(path, str) or not re.fullmatch(r"/assets/special/[a-z0-9-]+\.webp", path):
        return False
    file = ROOT / path.lstrip("/")
    return file.is_file() and 0 < file.stat().st_size <= 300000


def slide_block(standard, special):
    """Ten newest published photographic articles, not the original frozen 6+4."""
    candidates = []
    standard_rights = json.loads((ROOT / "standard-cover-manifest.json").read_text(encoding="utf-8")).get("articles", {})
    special_rights = json.loads((ROOT / "special-cover-manifest.json").read_text(encoding="utf-8")).get("articles", {})
    approved = json.loads((ROOT / "approved-special-articles.json").read_text(encoding="utf-8")).get("articles", [])

    for x in standard:
        slug = x["slug"]
        page = "news-" + slug + ".html"
        image = "/assets/special/news-" + slug + ".webp"
        rights = standard_rights.get("standard/" + slug, {}).get("origin", {})
        if (ROOT / page).is_file() and photo_ready(image) and rights.get("origin") == "Wikimedia Commons":
            candidates.append({"slug": "/" + page, "title": x["title"], "image": image,
                               "date": x.get("published_at") or x["date"]})

    for x in approved:
        if not x.get("editor_approved") or x.get("section") not in ("tech", "gaming"):
            continue
        slug = x["slug"]
        page = ("tech-impact-" if x["section"] == "tech" else "gaming-inside-") + slug + ".html"
        cover = special_rights.get(x["section"] + "/" + slug, {})
        image = cover.get("path", "")
        origin = cover.get("origin", {})
        if (ROOT / page).is_file() and photo_ready(image) and origin.get("origin") == "Wikimedia Commons":
            candidates.append({"slug": "/" + page, "title": x["title"], "image": image,
                               "date": x.get("published_at") or x["date"]})

    # Include any other original editorial NEWS with correctly licensed local photographs.
    manual = ROOT / "manual-news.json"
    if manual.exists():
        manual_items = json.loads(manual.read_text(encoding="utf-8")).get("items", [])
        for x in manual_items:
            slug, image = x.get("slug", ""), x.get("image", "")
            if (isinstance(slug, str) and re.fullmatch(r"news-[a-z0-9-]+\.html", slug)
                    and (ROOT / slug).is_file() and photo_ready(image)):
                candidates.append({"slug": "/" + slug, "title": x.get("title", "News ZazoomTek"),
                                   "image": image, "date": x.get("published_at") or x.get("date", "")})

    # Unique pages, newest first. Same-day ties retain input (editorial) order.
    by_slug = {}
    for item in candidates:
        if item["slug"] not in by_slug and publication_key(item["date"]):
            by_slug[item["slug"]] = item
    all_items = sorted(by_slug.values(), key=lambda x: publication_key(x["date"]), reverse=True)[:10]
    if not all_items:
        raise RuntimeError("No published articles with verified photographic covers")

    slides, tabs = [], []
    for i, item in enumerate(all_items):
        active = " active" if i == 0 else ""
        slides.append(
            '<article class="news-slide' + active + '" data-slide="' + str(i) + '"><a href="' + esc(item["slug"]) + '">'
            '<img src="' + esc(item["image"]) + '" alt="' + esc(item["title"]) + '" loading="lazy"></a></article>'
        )
        tabs.append(
            '<button class="news-tab' + active + '" data-go="' + str(i) + '">' + esc(item["title"]) + '</button>'
        )
    return ('<div class="news-slider" id="newsSlider"><div class="news-slides">'
        + "\n".join(slides) + '</div><div class="news-tabs">'
        + "\n".join(tabs) + '</div></div>')


def replace_between(s, begin, end, text):
    if s.count(begin) != 1 or s.count(end) != 1:
        raise RuntimeError("Page marker is missing or duplicated: " + begin)
    a = s.index(begin) + len(begin)
    b = s.index(end, a)
    return s[:a] + "\n" + text + "\n" + s[b:]


def standard_home_rows(standard):
    rows = []
    for x in standard:
        slug = "/news-" + x["slug"] + ".html"
        cover = "/assets/special/news-" + x["slug"] + ".webp"
        search = esc((x["title"] + " " + x["summary"]).lower())
        rows.append(
            '<article class="article-row" data-standard-news="true" data-search="' + search + '">'
            '<a href="' + esc(slug) + '"><img class="article-image" src="' + esc(cover) + '" alt="' + esc(x["title"]) + '" loading="lazy"></a>'
            '<div class="article-copy"><h3><a href="' + esc(slug) + '">' + esc(x["title"]) + '</a></h3>'
            '<div class="article-meta">ZazoomTek · 9 ottobre 2026</div><p>' + esc(x["summary"])
            + '</p><a class="read-more" href="' + esc(slug) + '">Leggi tutto ›</a></div></article>'
        )
    return "\n".join(rows)


def standard_news_rows(standard):
    rows = []
    for x in standard:
        slug = "/news-" + x["slug"] + ".html"
        cover = "/assets/special/news-" + x["slug"] + ".webp"
        rows.append(
            '<article class="news-row" data-standard-news="true" data-news-search="' + esc(x["title"].lower()) + '">'
            '<a href="' + esc(slug) + '"><img src="' + esc(cover) + '" alt="' + esc(x["title"]) + '" loading="lazy"></a>'
            '<div class="news-copy"><h2><a href="' + esc(slug) + '">' + esc(x["title"]) + '</a></h2>'
            '<div class="news-meta">ZazoomTek · 9 ottobre 2026</div><p>' + esc(x["summary"])
            + '</p><a class="news-read" href="' + esc(slug) + '">Leggi tutto ›</a></div></article>'
        )
    return "".join(rows)


def main():
    standard, special = load()
    s = INDEX.read_text(encoding="utf-8")
    s = replace_between(s, PAGE_START, PAGE_END, slide_block(standard, special))
    # Desktop has ten compact headlines; mobile retains its existing responsive rules.
    s = s.replace(
        ".news-tabs{display:grid;grid-template-rows:repeat(6,minmax(0,1fr))}",
        ".news-tabs{display:grid;grid-template-rows:repeat(10,minmax(0,1fr))}"
    )
    s = s.replace(
        ".news-tab{border:0;border-bottom:1px solid #333;background:#222;color:#fff;text-align:left;padding:14px 16px;cursor:pointer;font-size:.9rem;line-height:1.25}",
        ".news-tab{border:0;border-bottom:1px solid #333;background:#222;color:#fff;text-align:left;padding:7px 11px;cursor:pointer;font-size:.76rem;line-height:1.2}"
    )
    if ".news-tabs{display:grid;grid-template-rows:repeat(10,minmax(0,1fr))}" not in s:
        raise RuntimeError("Unable to set ten-row desktop carousel")
    # The importer fully rebuilds this region; reinsert manually approved posts on every run.
    feed = s[s.index(FEED_START) + len(FEED_START):s.index(FEED_END)]
    feed = re.sub(r'\s*' + re.escape(STANDARD_START) + r'.*?' + re.escape(STANDARD_END), '', feed, flags=re.S)
    # Normalize spacing on every run so a periodic YouTube sync doesn't
    # create meaningless diffs and unnecessary Firebase deployments.
    feed = STANDARD_START + '\n' + standard_home_rows(standard[:4]) + '\n' + STANDARD_END + '\n' + feed.strip()
    s = replace_between(s, FEED_START, FEED_END, feed)
    feature = s[s.index(PAGE_START):s.index(PAGE_END)]
    slide_count = len(re.findall(r'data-slide="\d+"', feature))
    if not 1 <= slide_count <= 10 or len(re.findall(r'data-go="\d+"', feature)) != slide_count:
        raise RuntimeError("Chronological carousel validation failed")
    if s.count('data-standard-news="true"') != 4:
        raise RuntimeError("Home NEWS count validation failed")

    news = NEWS.read_text(encoding="utf-8")
    # The Community publisher already reads manual-news.json; only add entries
    # missing from this particular generated file, never duplicate them.
    absent = [x for x in standard if 'href="/news-' + x["slug"] + '.html"' not in news]
    if absent:
        marker = '<div class="news-list" id="newsList">'
        if news.count(marker) != 1:
            raise RuntimeError("NEWS list not found, aborting safely")
        news = news.replace(marker, marker + standard_news_rows(absent), 1)
    for x in standard:
        if 'href="/news-' + x["slug"] + '.html"' not in news:
            raise RuntimeError("Standard NEWS missing from archive")

    if INDEX.read_text(encoding="utf-8") != s:
        INDEX.write_text(s, encoding="utf-8")
        print("Updated chronological featured NEWS carousel and latest approved articles.")
    if NEWS.read_text(encoding="utf-8") != news:
        NEWS.write_text(news, encoding="utf-8")
        print("Updated standard NEWS archive.")
    print(f"VALIDATED: {slide_count} latest photographic NEWS in publishing order; source importers unchanged.")


if __name__ == "__main__":
    main()
