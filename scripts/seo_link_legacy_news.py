#!/usr/bin/env python3
"""Keep old Community news in a separate minimal archive, linked only from the
last paginated News page, immediately below its final story. Never inject the
former oversized bullet list in /news.html."""
import argparse
import html
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

LEGACY = re.compile(r"<!-- ZT_SEO_ARCHIVE_LINKS_START -->[\s\S]*?<!-- ZT_SEO_ARCHIVE_LINKS_END -->", re.I)
LEGACY_SECTION = re.compile(r'<section\b[^>]*class=["\'][^"\']*\bzt-legacy-news-links\b[^"\']*["\'][^>]*>[\s\S]*?</section>', re.I)
CTA = re.compile(r"<!-- ZT_NEWS_ARCHIVE_CTA_START -->[\s\S]*?<!-- ZT_NEWS_ARCHIVE_CTA_END -->", re.I)
ROW = re.compile(r"news-Ugkx[A-Za-z0-9_-]+\.html")
PAGED = re.compile(r"news-(\d+)\.html")
PAGINATION = re.compile(r'<nav\b[^>]*class=["\'][^"\']*\barchive-pagination\b[^"\']*["\'][^>]*>[\s\S]*?</nav>', re.I)
MONTHS = ("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
          "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre")
LIST_HEAD = '<div class="news-list" id="newsList">'
ARCHIVE_CTA = (
    '<!-- ZT_NEWS_ARCHIVE_CTA_START -->'
    '<div class="zt-news-archive-cta" style="margin:16px 0 8px;text-align:center">'
    '<a href="/archivio-news.html" style="display:inline-flex;align-items:center;gap:8px;'
    'padding:12px 0;color:#252525;font-size:1rem;line-height:1.35;font-weight:700;'
    'text-decoration:none;border-bottom:2px solid #d51232">'
    'Archivio news <span aria-hidden="true" style="color:#d51232">›</span></a>'
    '</div><!-- ZT_NEWS_ARCHIVE_CTA_END -->'
)
ARCHIVE_CSS = """
<style id="zt-historical-news">
.zt-history-list{border:1px solid #e8e8e8;background:#fff}
.zt-history-link{display:flex;justify-content:space-between;gap:18px;align-items:baseline;
padding:12px 15px;border-bottom:1px solid #eee;text-decoration:none;
color:#282828;font-size:16px;line-height:1.45}
.zt-history-link:last-child{border-bottom:0}
.zt-history-link:hover,.zt-history-link:focus-visible{background:#fafafa;color:#b7132a}
.zt-history-link time{white-space:nowrap;font-size:12px;color:#777}
@media(max-width:700px){.zt-history-link{display:block}.zt-history-link time{display:block;margin-top:4px}}
</style>"""


def clean(document):
    return LEGACY_SECTION.sub("", LEGACY.sub("", CTA.sub("", document)))


def pages(root):
    results = [(1, root / "news.html")]
    results.extend((int(m.group(1)), f) for f in root.glob("news-[0-9]*.html")
                   if (m := PAGED.fullmatch(f.name)))
    return sorted(((n, f) for n, f in results if f.exists()), key=lambda x: x[0])


def list_range(document):
    a = document.find(LIST_HEAD)
    if a < 0:
        raise RuntimeError("News list missing")
    b = a + len(LIST_HEAD)
    m = re.search(r'</div>\s*<nav\b[^>]*class=["\'][^"\']*\barchive-pagination\b',
                  document[b:], re.I)
    if not m:
        raise RuntimeError("News list/pagination boundary missing")
    c = b + m.start()
    return a, b, c, c + len("</div>")


def publication(document):
    m = re.search(r'<meta\b[^>]*property=["\']article:published_time["\'][^>]*content=["\']([^"\']+)', document, re.I)
    if not m:
        m = re.search(r'"datePublished"\s*:\s*"([^"]+)"', document, re.I)
    if not m:
        return None, ""
    try:
        published = datetime.fromisoformat(m.group(1).replace("Z", "+00:00"))
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        local = published.astimezone(ZoneInfo("Europe/Rome"))
        return published, f"{local.day} {MONTHS[local.month-1]} {local.year}"
    except (ValueError, OverflowError):
        return None, ""


def historical_news(root, news_pages):
    active = set()
    for _, f in news_pages:
        page = f.read_text(encoding="utf-8")
        _, start, stop, _ = list_range(page)
        active.update(ROW.findall(page[start:stop]))
    found = []
    for f in root.glob("news-Ugkx*.html"):
        if not ROW.fullmatch(f.name) or f.name in active:
            continue
        page = f.read_text(encoding="utf-8", errors="replace")
        m = re.search(r'<title\b[^>]*>(.*?)</title\s*>', page, re.I | re.S)
        if not m:
            continue
        title = html.unescape(re.sub(r'<[^>]*>', ' ', m.group(1)))
        title = re.sub(r'\s*\|\s*ZazoomTek\s*$', '', ' '.join(title.split()), flags=re.I).strip()
        if title:
            date, label = publication(page)
            found.append((date, title, f.name, label))
    found.sort(key=lambda item: (item[0] or datetime.min.replace(tzinfo=timezone.utc), item[2]), reverse=True)
    return found


def archive_html(template, articles):
    original = clean(template)
    start, _, _, end = list_range(original)
    links = []
    for published, title, filename, date in articles:
        stamp = ('<time datetime="' + published.date().isoformat() + '">'
                 + html.escape(date) + '</time>') if published else ''
        links.append('<a class="zt-history-link" href="/' + html.escape(filename, quote=True)
                     + '"><span>' + html.escape(title) + '</span>' + stamp + '</a>')
    document = original[:start] + '<div class="zt-history-list" id="newsList">' + ''.join(links) + '</div>' + original[end:]
    document, count = PAGINATION.subn('', document, count=1)
    if count != 1:
        raise RuntimeError("Archive pagination removal failed")
    document = re.sub(r'<title>[^<]*</title>', '<title>Archivio news storico | ZazoomTek</title>', document, count=1)
    document = re.sub(r'<meta name="description" content="[^"]*">',
                      '<meta name="description" content="Archivio delle notizie precedenti pubblicate da ZazoomTek: tecnologia, videogiochi e Community.">',
                      document, count=1)
    document = re.sub(r'<link rel="canonical" href="[^"]+">',
                      '<link rel="canonical" href="https://zazoomtek.it/archivio-news.html">',
                      document, count=1)
    document = document.replace('<h1>Notizie</h1>', '<h1>Archivio news</h1>', 1)
    document = re.sub(r'<div class="news-filter">[\s\S]*?</div>', '', document, count=1)
    document = document.replace('</head>', ARCHIVE_CSS + '</head>', 1)
    if document.count('class="zt-history-link"') != len(articles):
        raise RuntimeError("Missing history links")
    return document


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    all_pages = pages(root)
    if not all_pages:
        raise RuntimeError("No News archive pages found")
    last_num, last_file = all_pages[-1]
    old_news = historical_news(root, all_pages)
    if not old_news:
        raise RuntimeError("The historical news archive would be empty")
    archive = archive_html(last_file.read_text(encoding="utf-8"), old_news)
    outputs = {root / "archivio-news.html": archive}
    for number, f in all_pages:
        page = clean(f.read_text(encoding="utf-8"))
        if number == last_num:
            _, _, _, end = list_range(page)
            page = page[:end] + ARCHIVE_CTA + page[end:]
        outputs[f] = page
    for path, content in outputs.items():
        if "Dall’archivio della Community" in content or "zt-legacy-news-links" in content:
            raise RuntimeError("Old list remains: " + path.name)
    if ARCHIVE_CTA not in outputs[last_file]:
        raise RuntimeError("Last News page missing its archive link")
    changed = 0
    for path, content in outputs.items():
        before = path.read_text(encoding="utf-8") if path.is_file() else None
        if before != content:
            changed += 1
            if not args.check:
                path.write_text(content, encoding="utf-8")
    print(f"Archive: {len(old_news)} older news; link after final story in News page {last_num}; files updated: {changed}; check: {args.check}")


if __name__ == "__main__":
    main()
