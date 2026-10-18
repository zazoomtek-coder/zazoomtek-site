#!/usr/bin/env python3
"""Build-only: preserve original Community/approved NEWS ISO publication time.

No new stories, no publication, no layout changes. Add data-published-at only
to known existing NEWS archive cards so the Home can place demoted carousel
stories correctly even when YouTube has not published anything new.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ARTICLE = re.compile(r'<article\b[^>]*\bclass="news-row"[^>]*>[\s\S]*?</article>', re.I)
TITLE_LINK = re.compile(r'<h2>\s*<a\s+href="/([^"/]+\.html)"', re.I)
OLD_TIME = re.compile(r'\sdata-published-at="[^"]*"')
VALID_SLUG = re.compile(r'news-[A-Za-z0-9_-]+\.html\Z')
VALID_POST_ID = re.compile(r'[A-Za-z0-9_-]{10,120}\Z')


def original_iso(value: object) -> str | None:
    if not isinstance(value, str) or "T" not in value.upper():
        return None  # Never manufacture an hour from a date-only label.
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def verified_times(root: Path) -> dict[str, str]:
    posts = json.loads((root / ".youtube-posts.json").read_text(encoding="utf-8"))
    if not isinstance(posts, list) or len(posts) < 50:
        raise RuntimeError("Published Community source missing; refusing timestamps")
    out: dict[str, str] = {}
    for post in posts:
        if not isinstance(post, dict):
            continue
        ident = post.get("id")
        if not isinstance(ident, str) or not VALID_POST_ID.fullmatch(ident):
            continue
        date = original_iso(post.get("published_iso") or post.get("published_at"))
        if date:
            out["news-" + ident + ".html"] = date

    manual_path = root / "manual-news.json"
    if manual_path.is_file():
        manual = json.loads(manual_path.read_text(encoding="utf-8"))
        for item in manual.get("items", []):
            if not isinstance(item, dict):
                continue
            slug, raw = item.get("slug"), item.get("published_at")
            if isinstance(slug, str) and VALID_SLUG.fullmatch(slug):
                date = original_iso(raw)
                if date:
                    out[slug] = date
    if len(out) < 30:
        raise RuntimeError("Too few verified NEWS publication timestamps; leaving archives unchanged")
    return out


def apply_to_markup(page: str, dates: dict[str, str]) -> tuple[str, int, int]:
    changed = 0
    matched = 0

    def update(match: re.Match[str]) -> str:
        nonlocal changed, matched
        block = match.group()
        linked = TITLE_LINK.search(block)
        if not linked:
            return block
        slug = linked.group(1)
        stamp = dates.get(slug)
        if not stamp:
            return block
        matched += 1
        open_end = block.find(">")
        opening, remaining = block[:open_end], block[open_end:]
        old = OLD_TIME.search(opening)
        if old:
            revised = opening[:old.start()] + opening[old.end():]
        else:
            revised = opening
        revised += ' data-published-at="' + escape(stamp, quote=True) + '"'
        updated = revised + remaining
        if updated != block:
            changed += 1
        return updated

    new = ARTICLE.sub(update, page)
    return new, changed, matched


def run(root: Path) -> None:
    dates = verified_times(root)
    updated = 0
    matched = 0
    found = 0
    for n in range(1, 6):
        path = root / ("news.html" if n == 1 else f"news-{n}.html")
        if not path.is_file():
            continue
        found += 1
        original = path.read_text(encoding="utf-8")
        revised, count, known = apply_to_markup(original, dates)
        matched += known
        updated += count
        if revised != original:
            path.write_text(revised, encoding="utf-8")
    if found == 0 or matched < 10:
        raise RuntimeError("Not enough verified archive cards; refusing incomplete chronology")
    print(f"Home archive chronology: {matched} verified original timestamps; {updated} card attributes refreshed")


def self_test() -> None:
    example = '<article class="news-row" data-news-search="news tech"><a href="/news-a.html"></a><div class="news-copy"><h2><a href="/news-a.html">A</a></h2></div></article>'
    dates = {"news-a.html": "2026-10-18T08:35:00Z"}
    changed, count, matched = apply_to_markup(example, dates)
    assert count == 1 and matched == 1
    assert 'data-published-at="2026-10-18T08:35:00Z"' in changed
    assert apply_to_markup(changed, dates) == (changed, 0, 1)
    assert original_iso("2026-10-18") is None
    assert original_iso("2026-10-18T10:35:00+02:00") == "2026-10-18T08:35:00Z"
    print("PASS: archive timestamp enhancement is idempotent, original-hour only")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    self_test() if args.self_test else run(args.root)
