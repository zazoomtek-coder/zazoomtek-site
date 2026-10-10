#!/usr/bin/env python3
"""Idempotent post-processing: six balanced featured NEWS, with daily updates.

Never imports YouTube, never edits review/video pages or special editorial content.
Call after the existing YouTube Community sync, which rewrites the homepage/NEWS.
"""
import html
import json
import re
from pathlib import Path
from datetime import datetime, timezone

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
    """Six independently sourced highlights: 2 Tech + 2 Gaming + 1 per special desk.

    The ordinary news are drawn ONLY from approved standard-news.json.
    The two special selections are read from special-featured.json, maintained
    by the independent Tech Impact / Gaming Inside publisher; never rewrite it.
    The 10-site trend matcher may subsequently reprioritize ordinary items,
    but must preserve this 2+2+1+1 quota.
    """
    standard_rights = json.loads((ROOT / "standard-cover-manifest.json").read_text(encoding="utf-8")).get("articles", {})
    special_rights = json.loads((ROOT / "special-cover-manifest.json").read_text(encoding="utf-8")).get("articles", {})
    chosen = []

    for kind in ("tech", "gaming"):
        items = [x for x in standard if x.get("kind") == kind][:2]
        if len(items) != 2:
            raise RuntimeError("Exactly two approved standard NEWS are required for " + kind)
        for x in items:
            slug = x["slug"]
            page = "/news-" + slug + ".html"
            image = "/assets/special/news-" + slug + ".webp"
            origin = standard_rights.get("standard/" + slug, {}).get("origin", {})
            if not (ROOT / page.lstrip("/")).is_file() or not photo_ready(image) or origin.get("origin") != "Wikimedia Commons":
                raise RuntimeError("Missing licensed standard NEWS cover or page: " + slug)
            chosen.append({"url": page, "title": x["title"], "image": image, "section": kind})

    for kind, section, prefix in (("tech", "tech-impact", "tech-impact-"),
                                  ("gaming", "gaming-inside", "gaming-inside-")):
        selected = [x for x in special if x.get("section") == kind]
        if not selected:
            raise RuntimeError("No existing " + section + " selection from the independent publisher")
        x = selected[0]  # Respect that publisher's featured priority.
        slug = x["slug"]
        key = kind + "/" + slug[len(prefix):-len(".html")]
        origin = special_rights.get(key, {}).get("origin", {})
        image = x.get("image", "")
        if (not slug.startswith(prefix) or not slug.endswith(".html")
                or not (ROOT / slug).is_file() or not photo_ready(image)
                or origin.get("origin") != "Wikimedia Commons"):
            raise RuntimeError("Missing licensed special page or cover: " + slug)
        chosen.append({"url": "/" + slug, "title": x["title"], "image": image, "section": section})

    if len(chosen) != 6 or len({x["url"] for x in chosen}) != 6:
        raise RuntimeError("Featured NEWS must contain six different articles")

    slides = []
    thumbnails = []
    for i, item in enumerate(chosen):
        active = " active" if i == 0 else ""
        image = str(item["image"])
        # A YouTube thumbnail normally already carries its editorial lettering.
        # All current featured artwork (standard news and specials) already has its title baked in.
        # Allow explicit future overrides for genuinely text-free images.
        has_text = item.get("cover_has_text", True) is not False
        cover_class = " zt-cover-with-text" if has_text else " zt-cover-needs-title"
        title = esc(re.sub(r"(?i)^news\\s*:\\s*", "", str(item["title"])))
        slides.append(
            '<article class="news-slide' + active + cover_class + '" data-cover-text="' + ('true' if has_text else 'false') + '" data-slide="' + str(i) +
            '" data-trend-category="' + esc(item["section"]) + '"><a href="' + esc(item["url"]) + '">'
            '<img src="' + esc(image) + '" alt="' + title + '" loading="lazy"></a></article>'
        )
        thumbnails.append(
            '<button type="button" class="zt-editorial-item" data-featured-index="' + str(i) +
            '" aria-label="Seleziona: ' + title + '"><img src="' + esc(image) +
            '" alt="" loading="lazy"><span class="zt-editorial-info"><span class="zt-editorial-headline">' +
            title + '</span></span></button>'
        )
    return ('<div class="news-slider" id="newsSlider"><div class="news-slides">'
            + "\n".join(slides) + '</div><div class="zt-editorial-side" aria-label="Altre notizie in evidenza">'
            + "".join(thumbnails) + '</div></div>')


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


def chronological_home_feed(original_feed, standard):
    """Merge the 15 imported Community articles with approved NEWS.

    Preserve the existing article HTML, but interleave by actual publication
    timestamp, instead of permanently pinning the four editorial articles.
    Do not change YouTube news, video or review importers.
    """
    row_pattern = r'<article\b[^>]*class="article-row"[^>]*>.*?</article>'
    imported_rows = re.findall(row_pattern, original_feed, flags=re.S)
    if len(imported_rows) < 4:
        raise RuntimeError("Latest Articles source feed is incomplete")

    state_file = ROOT / ".youtube-posts.json"
    if not state_file.is_file():
        raise RuntimeError("Community timestamp state is unavailable")
    posts = json.loads(state_file.read_text(encoding="utf-8"))
    if not isinstance(posts, list):
        raise RuntimeError("Invalid Community timestamp state")
    by_id = {p["id"]: p for p in posts if isinstance(p, dict) and isinstance(p.get("id"), str)}

    def when(raw):
        raw = str(raw or "").strip()
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).timestamp()
        except ValueError:
            date_only = publication_key(raw)
            if not date_only:
                return None
            try:
                return datetime.fromisoformat(date_only).replace(tzinfo=timezone.utc).timestamp()
            except ValueError:
                return None

    combined = []
    community_count = 0
    for row in imported_rows:
        # Remove already-injected manual entries before recombining; idempotent.
        if 'data-standard-news="true"' in row or 'data-manual-news="true"' in row:
            continue
        ref = re.search(r'href="/?(?:news|recensione)-(Ugkx[A-Za-z0-9_-]+)\.html"', row)
        if not ref:
            raise RuntimeError("Unable to identify a Community article in the home feed")
        post = by_id.get(ref.group(1))
        if post is None:
            raise RuntimeError("Missing Community timestamp for " + ref.group(1))
        timestamp = when(post.get("published_iso") or post.get("published"))
        if timestamp is None:
            raise RuntimeError("Invalid Community publication date for " + ref.group(1))
        combined.append((timestamp, row))
        community_count += 1

    manual_rows = re.findall(row_pattern, standard_home_rows(standard[:4]), flags=re.S)
    if len(manual_rows) != 4 or community_count < 5:
        raise RuntimeError("Expected four editorial NEWS and recent Community articles")
    for x, row in zip(standard[:4], manual_rows):
        # Prefer exact publication timestamps; date-only is midnight UTC, not
        # an invented time. New editorial articles should supply published_at.
        timestamp = when(x.get("published_at") or x.get("date"))
        if timestamp is None:
            raise RuntimeError("Invalid editorial publication date: " + x.get("slug", ""))
        combined.append((timestamp, row))

    # Independently written articles belong on Home as well as /news.html.
    manual_file = ROOT / "manual-news.json"
    manual_items = json.loads(manual_file.read_text(encoding="utf-8")).get("items", []) if manual_file.is_file() else []
    if not isinstance(manual_items, list):
        raise RuntimeError("Invalid manual NEWS registry")
    existing_links = set(re.findall(r'href="/?(news-[a-z0-9-]+\.html)"', "\n".join(row for _, row in combined)))
    new_manual = 0
    for x in manual_items:
        if not isinstance(x, dict):
            continue
        slug = x.get("slug", "")
        if not isinstance(slug, str) or not re.fullmatch(r"news-[a-z0-9-]+\.html", slug):
            continue
        if slug in existing_links or not (ROOT / slug).is_file():
            continue
        timestamp = when(x.get("published_at") or x.get("date"))
        if timestamp is None:
            raise RuntimeError("Manual NEWS lacks a valid publication date: " + slug)
        title = esc(x.get("title") or "News ZazoomTek")
        image = esc(x.get("image") or "/ChatGPT.png")
        excerpt = esc(x.get("excerpt") or "")
        date = esc(x.get("date") or "")
        search = esc((str(x.get("title") or "") + " " + str(x.get("excerpt") or "")).lower())
        row = ('<article class="article-row" data-manual-news="true" data-search="' + search + '">'
               '<a href="/' + slug + '"><img class="article-image" src="' + image + '" alt="' + title + '" loading="lazy"></a>'
               '<div class="article-copy"><h3><a href="/' + slug + '">' + title + '</a></h3>'
               '<div class="article-meta">ZazoomTek · ' + date + '</div><p>' + excerpt
               + '</p><a class="read-more" href="/' + slug + '">Leggi tutto ›</a></div></article>')
        combined.append((timestamp, row))
        existing_links.add(slug)
        new_manual += 1

    combined.sort(key=lambda pair: pair[0], reverse=True)
    merged = "\n".join(row for _, row in combined[:15])
    if merged.count('class="article-row"') != 15:
        raise RuntimeError("Home must contain exactly 15 latest articles")
    print(f"Latest Articles chronological: {community_count} Community + 4 standard + {new_manual} independent NEWS.")
    return STANDARD_START + "\n" + merged + "\n" + STANDARD_END


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
    # The importer rewrites HTML, so enforce the full-width photo layout on every sync.
    # Preserve existing responsive layout and the approved right-hand news column.
    s, slider_changes = re.subn(
        r"\.news-slider\{[^}]*\}",
        ".news-slider{display:block;width:100%;background:#111}", s, count=1
    )
    # Preserve the approved compact hero height after Community refreshes.
    s, hero_changes = re.subn(
        r"\.news-slides\{[^}]*\}",
        ".news-slides{position:relative;aspect-ratio:2.08/1;min-height:0;overflow:hidden;background:#111}", s, count=1
    )
    if hero_changes != 1:
        raise RuntimeError("Featured NEWS slide dimensions missing")
    s = s.replace(".news-slides{min-height:0;aspect-ratio:16/9}", ".news-slides{min-height:0;aspect-ratio:2.08/1}")
    if ".latest-reviews-module .video-card{flex-basis:" not in s:
        s = s.replace("</style>", """
.latest-reviews-module .video-card{flex-basis:calc((100% - 16px)/2)}
.latest-reviews-module .video-card h3{font-size:1.12rem;line-height:1.35;padding:16px 16px 20px}
@media(max-width:580px){.latest-reviews-module .video-card{flex-basis:88%}.news-slides{aspect-ratio:16/9}}
</style>""", 1)
    s, tabs_changes = re.subn(
        r"\.news-tabs\{[^}]*\}",
        ".news-tabs{display:none!important}", s, count=1
    )
    s, image_changes = re.subn(
        r"\.news-slide img\{[^}]*\}",
        ".news-slide img{width:100%;height:100%;object-fit:cover;object-position:center 28%;display:block;filter:none}",
        s, count=1
    )
    if slider_changes != 1 or tabs_changes != 1 or image_changes != 1:
        raise RuntimeError("Unable to enforce photo-only full-width NEWS carousel")
    # Reorder the actual existing articles; never pin manual news at the top.
    feed = s[s.index(FEED_START) + len(FEED_START):s.index(FEED_END)]
    feed = chronological_home_feed(feed, standard)
    s = replace_between(s, FEED_START, FEED_END, feed)
    feature = s[s.index(PAGE_START):s.index(PAGE_END)]
    slide_count = len(re.findall(r'data-slide="\d+"', feature))
    if slide_count != 6 or 'class="news-tab' in feature:
        raise RuntimeError("Full-width photo-only carousel validation failed")
    home_feed=s[s.index(FEED_START)+len(FEED_START):s.index(FEED_END)]
    if len(re.findall(r'<article\b[^>]*class="article-row"',home_feed)) != 15:
        raise RuntimeError("Home must show exactly 15 article rows")

    # Special/oversight stories belong only to their dedicated archives.
    # The four ordinary news (two tech and two gaming) belong in NEWS.
    news = NEWS.read_text(encoding="utf-8")
    special_urls = ["/" + x["slug"] for x in special]
    if any('href="' + url + '"' in news for url in special_urls):
        raise RuntimeError("Political Tech Impact/Gaming Inside story leaked into NEWS")
    # The Community importer builds the chronological News archive from
    # manual-news.json. Do not prepend rows here, which would break dates.
    if INDEX.read_text(encoding="utf-8") != s:
        INDEX.write_text(s, encoding="utf-8")
        print("Updated chronological featured NEWS carousel and latest approved articles.")
    if NEWS.read_text(encoding="utf-8") != news:
        NEWS.write_text(news, encoding="utf-8")
        print("Updated standard NEWS archive.")
    print(f"VALIDATED: {slide_count} NEWS (2 tech, 2 gaming, 1 Tech Impact, 1 Gaming Inside); independent special publisher unchanged.")


if __name__ == "__main__":
    main()
