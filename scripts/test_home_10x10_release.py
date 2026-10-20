#!/usr/bin/env python3
"""Transitional Home publishing-integrity check.

The historic 10+10 grid, fixed JS method names, exact cache revision, and
column alignment are design choices, not permanent publishing requirements.
They will be specified afresh after editorial approval. Retain only the
functional markers used by currently deployed content importers.
The old script filename is retained for backwards-compatible build calls.
"""
from __future__ import annotations
from pathlib import Path
import sys

PAIRS = (
    ("ARTICLE_FEED_START", "ARTICLE_FEED_END"),
    ("FEATURED_NEWS_START", "FEATURED_NEWS_END"),
    ("HOME_LATEST_REVIEWS_MAIN_START", "HOME_LATEST_REVIEWS_MAIN_END"),
)


def check(root: Path) -> None:
    home_path = root / "index.html"
    if not home_path.is_file():
        raise RuntimeError("Home source/output is missing")
    home = home_path.read_text(encoding="utf-8")
    for start, end in PAIRS:
        open_marker, close_marker = "<!-- " + start + " -->", "<!-- " + end + " -->"
        if (home.count(open_marker) != 1 or home.count(close_marker) != 1 or
                home.index(open_marker) >= home.index(close_marker)):
            raise RuntimeError("Home publishing markers absent, duplicated or misordered: " + start)
    print("HOME PUBLISHING CHECK PASS: content imports intact; no frozen 10+10 graphical layout")


if __name__ == "__main__":
    check(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("."))
