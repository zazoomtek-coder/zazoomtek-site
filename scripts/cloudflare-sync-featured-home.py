#!/usr/bin/env python3
"""Synchronize the actual homepage six-card grid with approved featured JSON.

Build-time only. The four-hour curator exclusively owns featured-carousel.json;
this script never selects stories or changes article text. A bad manifest stops
the deployment before visitors can see stale/missing cards. No runtime JS added.
"""
from __future__ import annotations

import argparse
import datetime as dt
from html import escape
import json
from pathlib import Path
from zoneinfo import ZoneInfo
import re

ROOT = Path(__file__).resolve().parents[1]
START = "<!-- FEATURED_NEWS_START -->"
END = "<!-- FEATURED_NEWS_END -->"
URL = re.compile(r"/[A-Za-z0-9_.-]+\.html\Z")
SECTION = {"tech", "gaming", "tech-impact", "gaming-inside"}

def render(root: Path) -> str:
    data = json.loads((root / "featured-carousel.json").read_text(encoding="utf-8"))
    pins = json.loads((root / "featured-editorial-pins.json").read_text(encoding="utf-8"))
    items = data.get("items")
    pinned = pins.get("items")
    if not isinstance(items, list) or len(items) > 6:
        raise RuntimeError("Featured carousel cannot exceed six cards")
    if not isinstance(pinned, list) or len(pinned) > 2:
        raise RuntimeError("Invalid editorial featured pins")
    pin_sections = [x.get("section") for x in pinned if isinstance(x, dict)]
    if len(pin_sections) != len(pinned) or len(set(pin_sections)) != len(pin_sections):
        raise RuntimeError("Duplicate or malformed editorial pins")
    if any(x not in ("tech-impact", "gaming-inside") for x in pin_sections):
        raise RuntimeError("Only special articles can be manually pinned")
    sections=[x.get("section") for x in items]
    regular=items[:-len(pinned)] if pinned else items
    ordinary=[x.get("section") for x in regular]
    tech_count=ordinary.count("tech")
    game_count=ordinary.count("gaming")
    # Preserve original editorial categories: more than one Gaming story is
    # allowed ONLY when fresh Tech does not fill the six visible cards.
    if (tech_count > 5-len(pinned)
            or game_count > 6-len(pinned)-tech_count
            or len(ordinary) != tech_count+game_count):
        raise RuntimeError("Featured JSON contains invalid Tech/Gaming fallback quotas")
    if [(x.get("section"),x.get("url")) for x in items[len(regular):]] != [
            (x.get("section"),x.get("url")) for x in pinned]:
        raise RuntimeError("Editorial special pin was removed without permission")
    if len({x.get("url") for x in items}) != len(items):
        raise RuntimeError("Featured articles are duplicated")
    today=dt.datetime.now(ZoneInfo("Europe/Rome")).date()
    for item in regular:
        try:
            day=dt.date.fromisoformat(item.get("published_date",""))
        except (TypeError,ValueError):
            raise RuntimeError("Featured regular article has no verified publication date")
        if day not in (today,today-dt.timedelta(days=1)):
            raise RuntimeError("Outdated featured article: "+str(item.get("url")))

    cards = []
    for n, item in enumerate(items):
        title = item.get("title")
        url = item.get("url")
        image = item.get("image")
        if not isinstance(title, str) or not title.strip():
            raise RuntimeError("Featured article has no title")
        if not isinstance(url, str) or not URL.fullmatch(url) or not (root / url.lstrip("/")).is_file():
            raise RuntimeError("Featured article missing or invalid: " + str(url))
        if not isinstance(image, str) or not image:
            raise RuntimeError("Featured article lacks a cover")
        if image.startswith("/"):
            if not image.startswith("/assets/") or not (root / image.lstrip("/")).is_file():
                raise RuntimeError("Featured local cover missing: " + image)
        elif not image.startswith("https://"):
            raise RuntimeError("Featured remote cover is not HTTPS")
        label = escape(re.sub(r"(?i)^news\s*:\s*", "", title), quote=True)
        path = escape(url, quote=True)
        cover = escape(image, quote=True)
        cards.append('<a class="zt-feature-card zt-feature-small" href="' + path +
                     '" aria-label="' + label + '" title="' + label +
                     '"><img src="' + cover + '" alt="' + label + '" loading="' +
                     ("eager" if n == 0 else "lazy") +
                     '" decoding="async"></a>')
    return ('<div class="zt-featured-grid" id="ztFeaturedGrid" '
            'aria-label="News ZazoomTek in evidenza">' + "".join(cards) + "</div>")

def sync(root: Path, check: bool = False) -> bool:
    root = Path(root)
    source = root / "index.html"
    old = source.read_text(encoding="utf-8")
    if old.count(START) != 1 or old.count(END) != 1:
        raise RuntimeError("Home has missing or duplicate featured boundaries")
    start = old.index(START) + len(START)
    end = old.index(END, start)
    new = old[:start] + "\n" + render(root) + "\n" + old[end:]
    changed = new != old
    if changed and not check:
        source.write_text(new, encoding="utf-8")
    print("CLOUDFLARE FEATURED HOME:", "needs correction" if changed and check
          else "synchronized" if changed else "already current")
    if not check:
        assert sync(root, check=True) is False, "Featured output must be idempotent"
    return changed

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    sync(ROOT, check=args.check)

if __name__ == "__main__":
    main()
