#!/usr/bin/env python3
"""Refresh Home editorial cards from articles actually published by ZazoomTek.

No AI drafting, no fabricated news, no metric-free "most read" ranking.
Editorial boxes always select the newest real, link-checked published articles.
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
POST_CATEGORY_RE = re.compile(r'data-post-category="(gaming|tech)"', re.I)
NEWS_CATEGORY_RE = re.compile(r'news\s+(gaming|tech)(?:\s+(?:impact|inside))?\s*:', re.I)
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

def publication_key(item: dict) -> tuple[int, int, int, int, int, int]:
    """Use original ISO publication timestamps; otherwise the Italian date label."""
    raw = str(item.get("published_at") or item.get("date") or "").lower()
    iso = re.search(r"(20\d{2})-(\d{1,2})-(\d{1,2})(?:[t ](\d{2}):(\d{2})(?::(\d{2}))?)?", raw)
    if iso:
        return tuple(int(x or 0) for x in iso.groups())
    months = {name: n for n, name in enumerate(
        "gennaio febbraio marzo aprile maggio giugno luglio agosto settembre ottobre novembre dicembre".split(), 1)}
    italian = re.search(r"(\d{1,2})\s+("+ "|".join(months) +r")\s+(20\d{2})", raw)
    if italian:
        day, month, year = italian.groups()
        return (int(year), months[month], int(day), 0, 0, 0)
    return (0, 0, 0, 0, 0, 0)


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
        category_tag = POST_CATEGORY_RE.search(chunk)
        category_text = NEWS_CATEGORY_RE.search(chunk[:1800])
        category = (category_tag or category_text)
        category = category.group(1).lower() if category else None
        published_attr = re.search(r'data-published-at="([^"]+)"', chunk)
        output.append({"url": href, "title": title, "image": photo, "date": date,
                       "published_at": html.unescape(published_attr.group(1)) if published_attr else "",
                       "category": category})
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

def likely_home_column_urls() -> set[str]:
    """Reserve the newest genuine Tech/Gaming URLs before sidebar selection.

    The Home browser restores 10 per category from published archives and may
    load pages asynchronously. Exclude their newest candidates up front, so
    the sidebar receives OLDER news rather than six soon-to-be-hidden cards.
    The browser still performs final visible-page dedup after carousel rotation.
    """
    buckets: dict[str, dict[str, dict]] = {"tech": {}, "gaming": {}}
    pages=("index.html", "news.html", "news-2.html", "news-3.html",
           "news-4.html", "news-5.html",
           "pagina-2.html", "pagina-3.html", "pagina-4.html", "pagina-5.html")
    for page in pages:
        for item in extract(page):
            category=item.get("category")
            if category not in buckets:
                continue
            previous=buckets[category].get(item["url"])
            if previous is None or publication_key(item)>publication_key(previous):
                buckets[category][item["url"]]=item
    return {
        item["url"]
        for pool in buckets.values()
        for item in sorted(pool.values(),key=publication_key,reverse=True)[:8]
    }


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
    """Never promote yesterday/older above newer published editorial stories.

    The scheduled refresh still runs daily; its content changes only when a
    newer published article is available, not because an older one was rotated.
    Stable sorting retains archive order for articles sharing the same date.
    """
    if len(items) < count:
        raise RuntimeError(f"Insufficient distinct published content: need {count}, have {len(items)}")
    ranked = sorted(items, key=publication_key, reverse=True)
    return ranked[:count]

def esc(value: str) -> str:
    return html.escape(value, quote=True)


def editorial_category(item: dict) -> str:
    """Classify public editorials by the article's actual topic, not opaque video IDs."""
    title = item["title"].casefold()
    gaming_terms = ["ea sports fc","tower tactics","talos principle","ace combat","dragon’s dogma","dragon's dogma","call of duty","gta ","tekken","street fighter","nintendo","playstation","xbox","steam","gameplay","videogioc","gaming","sonic racing","fc 27","battlefield","ps5","ps4","wolverine","the witcher","chivalware","monster hunter","dead spin","forza horizon"]
    return "GAMING" if any(word in title for word in gaming_terms) else "TECNOLOGIA"

def popular_cards(items: list[dict]) -> str:
    out = []
    for item in items:
        title = esc(item["title"])
        category = "GAMING" if item.get("category") == "gaming" else "TECNOLOGIA" if item.get("category") == "tech" else editorial_category(item)
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
    # Featured cards are refreshed independently, so the chosen editorial
    # backfill must also exclude the CURRENT verified carousel, not merely
    # the 15 news in the canonical Home feed. Otherwise the next carousel
    # rotation can reintroduce a duplicate into DA NON PERDERE.
    manifest = json.loads((ROOT / "featured-carousel.json").read_text(encoding="utf-8"))
    featured_urls = {clean_url(x.get("url", "")) for x in manifest.get("items", [])}
    if len(featured_urls) != 5 or None in featured_urls:
        raise RuntimeError("Cannot refresh editorial boxes with invalid featured URLs")
    reserved = published_home | featured_urls | likely_home_column_urls()
    ordinary = []
    # More archive pages allow older real articles to fill the boxes when
    # the newest ones are already in the carousel or Tech/Gaming columns.
    for file in ("news.html", "news-2.html", "news-3.html", "news-4.html", "news-5.html",
                 "pagina-2.html", "pagina-3.html", "pagina-4.html", "pagina-5.html"):
        ordinary.extend(item for item in extract(file)
                        if not item["url"].startswith(("/tech-impact-","/gaming-inside-"))
                        and not re.match(r"^News\s+(?:Tech\s+Impact|Gaming\s+Inside)\s*:",
                                         item["title"],re.I))
    if any(item["url"].startswith(("/tech-impact-","/gaming-inside-")) for item in ordinary):
        raise RuntimeError("Special article leaked into ordinary Home boxes")
    ordinary = distinct(ordinary, reserved)
    if len(ordinary) < 12:
        raise RuntimeError("Too few independent published news for editorial freshness")
    # Prioritize each source's freshest published, category-correct stories.
    # Cross-section exclusion must happen BEFORE selection, not after it.
    tech = choose(distinct(extract("tech-today.html"), reserved), 4, today)
    # Keep distinct topic-specific homepage covers even when the category feed is regenerated.
    # These files are actual local SVG assets, not remote placeholders.
    tech_cover_overrides = {
        "/tech-impact-le-norme-ue-sull-ia-affrontano-il-primo-test-con-i-laboratori.html":
            "/assets/special/tech-impact-eu-ai-test-labs-original-20261014.svg",
        "/tech-impact-california-nuova-legge-vieta-l-uso-di-bot-e-intelligenza-artificiale-nei-licenziament.html":
            "/assets/special/tech-impact-california-ai-workplace-law-original-20261014.svg",
    }
    for item in tech:
        cover = tech_cover_overrides.get(item["url"])
        if cover and valid_image(cover):
            item["image"] = cover
    special_urls = {item["url"] for item in tech}
    gaming = choose(distinct(extract("gaming-today.html"), reserved | special_urls), 4, today)
    special_urls.update(item["url"] for item in gaming)
    ordinary = distinct(ordinary, reserved | special_urls)
    # Permanent editorial separation: DA NON PERDERE is TECH only and
    # DALLA REDAZIONE is GAMING only. Rely on explicit published category metadata,
    # not on guesses from cover artwork or ambiguous headlines.
    suggested = choose([item for item in ordinary if item["category"] == "tech"], 6, today)
    selected = {item["url"] for item in suggested}
    left = distinct(ordinary, reserved | special_urls | selected)
    editorial = choose([item for item in left if item["category"] == "gaming"], 12, today, keep_latest=2)
    if any(item["category"] != "tech" for item in suggested):
        raise RuntimeError("Non-Tech article reached DA NON PERDERE")
    if any(item["category"] != "gaming" for item in editorial):
        raise RuntimeError("Non-Gaming article reached DALLA REDAZIONE")
    if len(set(item["url"] for item in tech + gaming + suggested + editorial)) != 26:
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
    if editorial_category({"title": "EA SPORTS FC 27", "url": "/test.html"}) != "GAMING":
        raise RuntimeError("Gaming category classification failed")
    if editorial_category({"title": "Microsoft Maia AI", "url": "/test.html"}) != "TECNOLOGIA":
        raise RuntimeError("Tech category classification failed")
    if re.search(r'\\g<[12]>', homepage):
        raise RuntimeError("Found literal regex back-reference in published HTML")
    report = {"date_italy": today.isoformat(), "suggested": [x["url"] for x in suggested],
              "tech_impact": [x["url"] for x in tech],
              "gaming_inside": [x["url"] for x in gaming],
              "dalla_redazione": [x["url"] for x in editorial],
              "cards": {
                  "suggested": [{k: x[k] for k in ("title", "url", "image", "category")} for x in suggested],
                  "tech_impact": [{k: x[k] for k in ("title", "url", "image")} for x in tech],
                  "gaming_inside": [{k: x[k] for k in ("title", "url", "image")} for x in gaming],
                  "dalla_redazione": [{k: x[k] for k in ("title", "url", "image", "category")} for x in editorial],
              }}
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
        assert sum(len(report[key]) for key in ("suggested", "tech_impact", "gaming_inside", "dalla_redazione")) == 26
        assert not (set(report["suggested"]) & likely_home_column_urls()), "Popular sidebar reused a Tech/Gaming column article"
        assert not (set(report["suggested"]) & {clean_url(x["url"]) for x in json.loads((ROOT / "featured-carousel.json").read_text(encoding="utf-8"))["items"]}), "Popular sidebar reused a carousel article"
        print("PASS: every refreshed card uses a real existing ZazoomTek article + validated thumbnail")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not opts.self_test and not opts.dry_run:
        (ROOT / "index.html").write_text(index, encoding="utf-8")
        (ROOT / "zt-home-live.js").write_text(javascript, encoding="utf-8")

if __name__ == "__main__":
    main()
