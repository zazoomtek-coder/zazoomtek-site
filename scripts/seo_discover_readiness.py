#!/usr/bin/env python3
"""Read-only Google Discover readiness report for canonical editorial pages."""
import argparse
import json
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
from seo_paths_safe import html_pages, canonical_candidates
from seo_head_safe import Metadata

END_HEAD = re.compile(r"</head\s*>", re.I)
class Head(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.in_title = False
        self.image = []
    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs if k}
        if tag == "title": self.in_title = True
        if tag == "meta" and a.get("property","").lower() == "og:image":
            self.image.append(a.get("content","").strip())
    def handle_data(self, data):
        if self.in_title: self.title += data
    def handle_endtag(self, tag):
        if tag == "title": self.in_title = False

def image_width(root, url):
    target = urlsplit(url)
    if target.netloc not in ("zazoomtek.it", "www.zazoomtek.it"):
        return None
    local = (root / unquote(target.path).lstrip("/")).resolve()
    if not local.is_relative_to(root) or not local.is_file():
        return None
    try:
        from PIL import Image
        with Image.open(local) as img:
            return img.size
    except (ImportError, OSError, ValueError):
        return None

def audit(root):
    issues = []
    counts = Counter()
    for path in html_pages(root):
        name = path.name
        if name.startswith(("preview-", "anteprima-", "draft-")):
            continue
        # Paginated News archives are listings, not editorial articles.
        if re.fullmatch(r"news-[0-9]+\.html", name):
            continue
        original = path.read_text(encoding="utf-8", errors="replace")
        match = END_HEAD.search(original)
        if not match:
            continue
        head = original[:match.start()]
        meta = Metadata()
        meta.feed(head)
        if len(meta.canonicals) != 1 or meta.canonicals[0] not in canonical_candidates(root, path):
            continue
        robots = " ".join(meta.meta.get(k, "") for k in ("robots", "googlebot")).lower()
        if "noindex" in robots:
            continue
        if not (meta.meta.get("og:type","").lower() == "article" or
                name.startswith(("news-", "recensione-", "tech-impact-", "gaming-inside-", "guida-")) or
                "recensione" in name):
            continue
        counts["articles"] += 1
        parsed = Head()
        parsed.feed(head)
        def flag(key, detail):
            counts[key] += 1
            issues.append({"page": name, "issue": key, "detail": detail})
        if "max-image-preview:large" not in robots:
            flag("preview_permission_missing", "Missing large-image permission")
        if len(parsed.image) != 1:
            flag("og_image_missing_or_duplicate", f"Found {len(parsed.image)} images")
            continue
        url = parsed.image[0]
        parts = urlsplit(url)
        if parts.scheme != "https" or not parts.netloc:
            flag("image_url_invalid", url)
            continue
        if "chatgpt.png" in url.lower() or "logo" in parts.path.lower():
            flag("generic_cover", url)
        size = image_width(root, url)
        if size:
            width, height = size
            if width < 1200 or width * height <= 300000:
                flag("small_local_image", f"{width}x{height}: {url}")
            counts["locally_measured_images"] += 1
        else:
            counts["unmeasured_remote_or_missing_images"] += 1
            # Filename dimensions are evidence; HTML width attributes are not.
            named = re.search(r"(?:capsule_|header_|cover_)(\d{2,4})x(\d{2,4})", parts.path, re.I)
            if named and int(named.group(1)) < 1200:
                flag("undersized_named_remote_image", f"{named.group(1)}x{named.group(2)}: {url}")
    return {"counts": dict(counts), "findings": issues}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("."))
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    result = audit(args.root.resolve())
    if args.output:
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"counts":result["counts"],"sample":result["findings"][:25]}, ensure_ascii=False, indent=2))
if __name__ == "__main__":
    main()
