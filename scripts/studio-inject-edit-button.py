#!/usr/bin/env python3
"""Install the Studio quick-edit UI on all existing and newly generated site pages.

Rendering runs after YouTube / feed imports, so future articles receive the
same affordance without touching their editorial HTML or Home structure.
The JavaScript only displays edit controls to browsers with a Studio session.
Actual GitHub writes still require authentication in Studio.
"""
from __future__ import annotations
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TAG = '<script src="/studio/edit-button.js" defer></script>'
END = re.compile(r"</body\s*>", re.I)


def inject(root: Path = ROOT):
    count = 0
    for path in list(root.glob("*.html")) + list((root / "watch").glob("*.html")):
        if path.name.startswith(("preview-", "anteprima-", "audit-", "test-")):
            continue
        markup = path.read_text(encoding="utf-8")
        if not END.search(markup) or TAG in markup:
            continue
        # Archives and Home get edit controls on their article cards; article
        # pages additionally get the edit link beside the genuine title.
        if not re.search(r"<(?:main|article)\b", markup, re.I):
            continue
        new = END.sub(lambda m: TAG + "\n" + m.group(), markup, count=1)
        if new != markup:
            path.write_text(new, encoding="utf-8")
            count += 1
    print("Studio quick edit installed on source/YouTube/feed/archives:", count)
    return count


def self_test():
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        root = Path(t)
        (root / "index.html").write_text('<html><body><main>Home cards</main></body></html>')
        (root / "review.html").write_text('<html><body><main class="content"><h1>Review</h1><article class="article-body article-main">Review</article></main></body></html>')
        (root / "watch").mkdir()
        (root / "watch" / "abcdefghijk.html").write_text('<html><body><main><article class="zt-watch-article"><h1>Video</h1></article></main></body></html>')
        (root / "news-YT.html").write_text('<html><body><main><article class="story"><h1>YouTube News</h1></article></main></body></html>')
        assert inject(root) == 4
        assert inject(root) == 0
        for name in ("index.html", "review.html", "news-YT.html", "watch/abcdefghijk.html"):
            assert (root / name).read_text().count(TAG) == 1
        print("PASS: Homepage cards and all editorial page shapes receive Studio UI")


if __name__ == "__main__":
    import sys
    self_test() if "--self-test" in sys.argv else inject()
