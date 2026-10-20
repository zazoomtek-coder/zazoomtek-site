#!/usr/bin/env python3
"""Temporary, flexible Home integrity guard.

The old 18 October Home hash/FNV lock has been retired at the editor's request.
Approved CSS, inline styles, JS, cache revisions and graphic composition are
NOT compared with a frozen snapshot. A new editorial design contract will be
defined with the site owner separately.

Only verify that the publishing pipeline still has its functional HTML anchors
and that the Home is not truncated or referencing missing local scripts.
Runs on source and disposable Cloudflare dist. No production writes.
"""
from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
MARKER_PAIRS = (
    ("FEATURED_NEWS_START", "FEATURED_NEWS_END"),
    ("ARTICLE_FEED_START", "ARTICLE_FEED_END"),
    ("HOME_LATEST_REVIEWS_MAIN_START", "HOME_LATEST_REVIEWS_MAIN_END"),
)
REQUIRED_IDS = ("ztFeaturedGrid", "articleList")


class HomeLockError(RuntimeError):
    pass


class HomeElements(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = {}
        self.local_scripts = []

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        identifier = data.get("id")
        if identifier:
            self.ids[identifier] = self.ids.get(identifier, 0) + 1
        if tag == "script" and data.get("src", "").startswith("/"):
            self.local_scripts.append(data["src"])


def verify(root: Path = ROOT, packaged: bool = False) -> None:
    errors = []
    path = root / "index.html"
    if not path.is_file():
        raise HomeLockError("HOME INTEGRITY FAILED: missing index.html")
    home = path.read_text(encoding="utf-8")
    if len(home) < 1000 or not re.search(r"<html\\b", home, re.I):
        errors.append("Home is truncated or has no HTML document")
    for tag in ("head", "body", "html"):
        if not re.search(r"<" + tag + r"\\b", home, re.I):
            errors.append("Missing opening <" + tag + ">")
        if not re.search(r"</" + tag + r"\\s*>", home, re.I):
            errors.append("Missing closing </" + tag + ">")
    parser = HomeElements()
    parser.feed(home)
    for ident in REQUIRED_IDS:
        if parser.ids.get(ident, 0) != 1:
            errors.append(f"Required publishing anchor #{ident} missing/duplicate")
    for start, end in MARKER_PAIRS:
        a, b = "<!-- " + start + " -->", "<!-- " + end + " -->"
        if home.count(a) != 1 or home.count(b) != 1 or home.index(a) > home.index(b):
            errors.append("Missing/duplicated/misordered publishing markers: " + start)
    for url in parser.local_scripts:
        parsed = urlsplit(url)
        name = parsed.path.lstrip("/")
        if ".." in Path(name).parts or not (root / name).is_file():
            errors.append("Missing/unsafe local Home script: " + url)
    if errors:
        raise HomeLockError("HOME INTEGRITY FAILED:\\n" + "\\n".join("- " + x for x in errors))
    label = "packaged Cloudflare dist" if packaged else "source checkout"
    print(f"HOME INTEGRITY PASS ({label}): publishing anchors intact; CSS/JS/design unlocked.")


def self_test() -> None:
    def sample(style):
        return (
            '<!DOCTYPE html><html><head><title>Test</title>'
            f'<style>{style}</style></head><body>'
            '<div id="ztFeaturedGrid"></div><div id="articleList"></div>'
            '<!-- FEATURED_NEWS_START --><!-- FEATURED_NEWS_END -->'
            '<!-- ARTICLE_FEED_START --><!-- ARTICLE_FEED_END -->'
            '<!-- HOME_LATEST_REVIEWS_MAIN_START -->'
            '<!-- HOME_LATEST_REVIEWS_MAIN_END -->'
            '<script src="/new-layout.js?v=9999"></script>'
            '</body></html>'
        )
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        (root / "new-layout.js").write_text("console.log('new layout')", encoding="utf-8")
        index = root / "index.html"
        index.write_text(sample("body{border-radius:0}"), encoding="utf-8")
        verify(root)
        index.write_text(sample("body{border-radius:34px;color:red}"), encoding="utf-8")
        (root / "new-layout.js").write_text("console.log('changed')", encoding="utf-8")
        verify(root)
        index.write_text(sample("body{}").replace("ARTICLE_FEED_END", "BROKEN_MARKER"), encoding="utf-8")
        try:
            verify(root)
        except HomeLockError:
            pass
        else:
            raise AssertionError("Must reject missing import marker")
    print("HOME FLEXIBLE INTEGRITY SELF-TEST PASS")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--packaged", action="store_true")
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    if args.self_test:
        self_test()
    else:
        verify(ROOT / "dist" if args.packaged else ROOT, packaged=args.packaged)


if __name__ == "__main__":
    main()
