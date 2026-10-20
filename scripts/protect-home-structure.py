#!/usr/bin/env python3
"""Protect usable Home publishing output without imposing a visual layout.

Temporary rules until the editor approves the new Home design contract.
No three-column requirement, fixed class names, rigid graphic blocks or exact
pixel/asset revisions. Editors may redesign without bypassing this guard.
"""
from pathlib import Path
import sys

PAIRS = (
    ("FEATURED_NEWS_START", "FEATURED_NEWS_END"),
    ("ARTICLE_FEED_START", "ARTICLE_FEED_END"),
    ("HOME_LATEST_REVIEWS_MAIN_START", "HOME_LATEST_REVIEWS_MAIN_END"),
)


def check(path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"HOME GUARD: missing {path}")
    text = path.read_text(encoding="utf-8")
    if len(text) < 1000 or "<body" not in text.lower() or "</body>" not in text.lower():
        raise SystemExit(f"HOME GUARD: broken/truncated HTML: {path}")
    for start, end in PAIRS:
        first, last = "<!-- " + start + " -->", "<!-- " + end + " -->"
        if (text.count(first) != 1 or text.count(last) != 1 or
                text.index(first) >= text.index(last)):
            raise SystemExit("HOME GUARD: missing/duplicated publishing boundary " + start)
    if 'id="ztFeaturedGrid"' not in text or 'id="articleList"' not in text:
        raise SystemExit("HOME GUARD: news publishing targets are missing")
    print(f"HOME GUARD OK: {path} — content publishing intact; Home composition editable.")


if __name__ == "__main__":
    for candidate in sys.argv[1:] or ["index.html"]:
        check(Path(candidate))
