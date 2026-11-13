"""Non-blocking cleanup for orphaned historical Community anchors."""
import re
from html import unescape
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit


class _AnchorCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.hrefs.append(href)


def _pretty(path):
    return path.removesuffix(".html").rstrip("/") or "/"


def strip_orphan_community_anchors(markup, existing_routes):
    """Remove only <a> wrappers for missing /community-* targets.

    Anchor contents (including nested formatting elements and visible text)
    are preserved. Existing Community destinations are left untouched.
    Returns (rewritten_markup, warning_messages).
    """
    existing = {str(route).lstrip("/") for route in existing_routes}
    parser = _AnchorCollector()
    parser.feed(markup)

    orphan_hrefs = set()
    warnings = []
    for href in parser.hrefs:
        parsed = urlsplit(href)
        if parsed.scheme or parsed.netloc or not href.startswith("/"):
            continue
        path = _pretty(unquote(parsed.path))
        if path.startswith("/community-") and path.lstrip("/") not in existing:
            orphan_hrefs.add(href)
            warnings.append(path)

    if not orphan_hrefs:
        return markup, []

    anchor = re.compile(r"<a\b(?P<attrs>[^>]*)>(?P<inner>.*?)</a\s*>", re.I | re.S)
    href_attr = re.compile(r"""\bhref\s*=\s*(["'])(.*?)\1""", re.I | re.S)

    def unwrap(match):
        attr = href_attr.search(match.group("attrs"))
        if attr and unescape(attr.group(2)) in orphan_hrefs:
            return match.group("inner")
        return match.group(0)

    cleaned = anchor.sub(unwrap, markup)
    return cleaned, sorted(set(warnings))
