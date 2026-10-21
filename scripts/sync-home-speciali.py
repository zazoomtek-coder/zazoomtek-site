#!/usr/bin/env python3
"""Sync the Home SPECIALI box from actually approved/published speciali.html.

Only Home markup between the dedicated SPECIALI card markers is updated.
Never creates articles, invents a second one or changes the source archive.
Run after build-speciali.py in each Cloudflare build, so the next approved
special automatically occupies the second available place (maximum two).
"""
from __future__ import annotations
import html
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_START = "<!-- ZT_SPECIALI_ITEMS_START -->"
ARCHIVE_END = "<!-- ZT_SPECIALI_ITEMS_END -->"
HOME_START = "<!-- HOME_SPECIALI_CARDS_START -->"
HOME_END = "<!-- HOME_SPECIALI_CARDS_END -->"
ROW = re.compile(r'<article\b[^>]*\bdata-zt-special="approved"[^>]*>.*?</article>', re.I | re.S)
TITLE = re.compile(r'<h2\b[^>]*>\s*<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.I | re.S)
IMAGE = re.compile(r'<img\b[^>]*\bsrc="([^"]+)"', re.I | re.S)
DATE = re.compile(r'<div\b[^>]*class="news-meta"[^>]*>(.*?)</div>', re.I | re.S)
LOCAL_URL = re.compile(r'^/[a-zA-Z0-9_.-]+\.html$')


def special_cards(archive: str) -> list[dict[str,str]]:
    if archive.count(ARCHIVE_START) != 1 or archive.count(ARCHIVE_END) != 1:
        raise RuntimeError("Speciali archive is missing its approved-items markers")
    content = archive.split(ARCHIVE_START, 1)[1].split(ARCHIVE_END, 1)[0]
    found, seen = [], set()
    for row in ROW.findall(content):
        title, image = TITLE.search(row), IMAGE.search(row)
        if not title or not image:
            raise RuntimeError("Approved Speciale is missing its title or image")
        url, caption, src = html.unescape(title.group(1)), html.unescape(
            re.sub(r'<[^>]+>', '', title.group(2)).strip()), html.unescape(image.group(1))
        if not LOCAL_URL.fullmatch(url) or not caption:
            raise RuntimeError("Invalid published Speciale URL or heading")
        if not (src.startswith("/assets/") or src.startswith("https://")):
            raise RuntimeError("Speciale image source is not valid")
        if url in seen:
            continue
        seen.add(url)
        meta = DATE.search(row)
        date = html.unescape(re.sub(r'<[^>]+>', '', meta.group(1)).strip()) if meta else ""
        found.append({"url":url, "title":caption, "image":src, "date":date})
        if len(found) == 2:
            break
    return found


def render(cards: list[dict[str,str]], root: Path) -> str:
    if not cards:
        raise RuntimeError("No real published Speciale: leave existing Home unchanged")
    out = []
    for item in cards:
        url = item["url"]
        if not (root / url.lstrip("/")).is_file():
            raise RuntimeError("Speciale is not published locally: " + url)
        src = item["image"]
        if src.startswith("/") and not (root / src.lstrip("/")).is_file():
            raise RuntimeError("Speciale image is missing: " + src)
        title = html.escape(item["title"], quote=True)
        href = html.escape(url, quote=True)
        image = html.escape(src, quote=True)
        out.append(
            '<article class="zt-special-item">'
            '<a href="' + href + '" class="zt-special-thumb" aria-label="' + title + '">'
            '<img src="' + image + '" alt="' + title + '" loading="lazy" '
            'decoding="async" width="160" height="90"></a>'
            '<h3><a href="' + href + '">' + title + '</a></h3></article>')
    return "\n".join(out)


def sync(root: Path = ROOT, check: bool = False) -> bool:
    root = Path(root)
    page = root / "index.html"
    source = page.read_text(encoding="utf-8")
    if source.count(HOME_START) != 1 or source.count(HOME_END) != 1:
        raise RuntimeError("Home SPECIALI markers missing or duplicate")
    cards = special_cards((root / "speciali.html").read_text(encoding="utf-8"))
    inner = "\n" + render(cards, root) + "\n"
    a = source.index(HOME_START) + len(HOME_START)
    b = source.index(HOME_END, a)
    updated = source[:a] + inner + source[b:]
    changed = source != updated
    if changed and not check:
        page.write_text(updated, encoding="utf-8")
    print(f"HOME SPECIALI: {len(cards)} genuine article(s); "
          + ("change needed" if check and changed else
             "updated" if changed else "already synchronized"))
    return changed


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    sync(ROOT, check=args.check)
