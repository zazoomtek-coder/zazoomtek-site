#!/usr/bin/env python3
"""Remove visually duplicate article images, preserving distinct photos and metadata."""
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit, unquote
from urllib.request import Request, urlopen
import re

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
HERO = re.compile(r'<img\b(?=[^>]*class=["\'][^"\']*article-hero)[^>]*>', re.I)
FIGURE = re.compile(r'<figure\b[^>]*class=["\'][^"\']*article-inline-media[^"\']*["\'][^>]*>.*?</figure>', re.I | re.S)
IMG = re.compile(r'<img\b[^>]*>', re.I)
SRC = re.compile(r'\bsrc=["\']([^"\']+)["\']', re.I)
HASHES = {}
ALIASES = {
    "7esQLR53uJ9x0_gVYh0cE6maRvHLntmOeUeeGOdjN7LJmbXwsC6VbJSFOWfBf2qEGLR6QFT5bew":
    "ahl8LogGQOGEgxY-BQrojHMfWHiMH7uV9uAbfUwXHrTw3dRywRKUFpzneYc6RDhdS48IHI70buVi4g",
}


def src(markup):
    match = IMG.search(markup)
    if not match:
        return ""
    url = SRC.search(match.group(0))
    return unescape(url.group(1)) if url else ""


def identity(url):
    parts = urlsplit(url)
    path = unquote(parts.path)
    if parts.hostname in ("yt3.ggpht.com", "yt3.googleusercontent.com", "lh3.googleusercontent.com"):
        path = re.sub(r'=s\d+(?:[-=].*)?$', '', path)
    image_id = path.rsplit("/", 1)[-1]
    image_id = ALIASES.get(image_id, image_id)
    return (parts.hostname, image_id)


def fingerprint(url):
    if url in HASHES:
        return HASHES[url]
    value = None
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=3) as response:
            raw = response.read(2500001)
        if len(raw) <= 2500000:
            with Image.open(BytesIO(raw)) as image:
                im = ImageOps.exif_transpose(image).convert("L").resize((9, 8))
                px = list(im.getdata())
                value = sum(1 << (row*8+col) for row in range(8) for col in range(8)
                            if px[row*9+col] > px[row*9+col+1])
    except Exception:
        pass  # Never delete if the comparison cannot be verified.
    HASHES[url] = value
    return value


def duplicate(url, previous):
    if any(identity(url) == identity(other) for other in previous):
        return True
    candidate = fingerprint(url)
    if candidate is None:
        return False
    for other in previous:
        prior = fingerprint(other)
        if prior is not None and (candidate ^ prior).bit_count() <= 2:
            return True
    return False


def clean(path):
    source = path.read_text(encoding="utf-8")
    hero = HERO.search(source)
    figures = list(FIGURE.finditer(source))
    if not hero or not figures:
        return 0
    cover = src(hero.group(0))
    seen = [cover] if cover else []
    changes = []
    for figure in figures:
        url = src(figure.group(0))
        if not url:
            continue
        if duplicate(url, seen):
            changes.append((figure.start(), figure.end()))
        else:
            seen.append(url)
    if changes:
        for start, end in reversed(changes):
            source = source[:start] + source[end:]
        path.write_text(source, encoding="utf-8")
    return len(changes)


def main():
    pages = sorted(ROOT.glob("news-*.html")) + sorted(ROOT.glob("recensione-*.html"))
    pages += sorted(ROOT.glob("*-recensione-*.html"))
    pages = list(dict.fromkeys(pages))
    checked = 0
    removed = 0
    # The image cache remains local to this run; failures never cause deletion.
    for page in pages:
        count = clean(page)
        checked += 1
        removed += count
        if count:
            print(f"{page.name}: removed {count} duplicate image(s)")
    print(f"Checked {checked} article pages; removed {removed} duplicated inline images.")


if __name__ == "__main__":
    main()
