#!/usr/bin/env python3
"""Safe head-only JSON-LD completion for ZazoomTek. Idempotent, no page-body edits."""
import argparse
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from seo_paths_safe import html_pages, canonical_candidates
from seo_head_safe import Metadata

ORIGIN = "https://zazoomtek.it"
MARKER = "<!-- ZT_SCHEMA_COMPLETION_V1 -->"
HEAD_END = re.compile(r"</head\s*>", re.I)
LD = re.compile(r'<script\b[^>]*\btype\s*=\s*["\']application/ld\+json["\'][^>]*>(.*?)</script\s*>', re.I | re.S)
CATEGORY = {
    "news-": ("News", "news.html"),
    "recensione-": ("Recensioni", "recensioni.html"),
    "gaming-inside-": ("Gaming Inside", "gaming-inside.html"),
    "tech-impact-": ("Tech Impact", "tech-impact.html"),
    "guida-": ("Guide", "guide.html"),
}
ARCHIVE = {
    "news.html", "recensioni.html", "gaming.html", "guide.html",
    "test.html", "unboxing.html", "gaming-inside.html", "tech-impact.html",
}
class Heading(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag.lower() == "h1":
            self.depth += 1
    def handle_endtag(self, tag):
        if tag.lower() == "h1" and self.depth:
            self.depth -= 1
    def handle_data(self, data):
        if self.depth:
            self.parts.append(data)

def types(document):
    result = set()
    def walk(node):
        if isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            values = node.get("@type", [])
            result.update([values] if isinstance(values, str) else [x for x in values if isinstance(x, str)] if isinstance(values, list) else [])
            if "@graph" in node:
                walk(node["@graph"])
    walk(document)
    return result

def transform(path, root, source):
    if path.name.startswith(("preview-", "anteprima-", "draft-")) or MARKER in source:
        return source
    match = HEAD_END.search(source)
    if not match:
        return source
    head, remainder = source[:match.start()], source[match.start():]
    info = Metadata()
    info.feed(head)
    if len(info.canonicals) != 1 or info.canonicals[0] not in canonical_candidates(root, path):
        return source
    robots = " ".join(info.meta.get(x, "") for x in ("robots", "googlebot")).lower()
    if re.search(r"(?<![a-z])(?:noindex|none)(?![a-z])", robots):
        return source
    seen = set()
    for item in LD.findall(head):
        try:
            seen |= types(json.loads(html.unescape(item)))
        except (ValueError, TypeError):
            return source   # malformed existing JSON-LD: do not compound the issue
    canonical = info.canonicals[0]
    new = []
    if path.name == "index.html":
        if "Organization" not in seen:
            new.append({"@context":"https://schema.org","@type":"Organization",
                "@id":ORIGIN+"/#organization","name":"ZazoomTek","url":ORIGIN+"/",
                "logo":{"@type":"ImageObject","url":ORIGIN+"/ChatGPT.png"}})
        if "WebSite" not in seen:
            new.append({"@context":"https://schema.org","@type":"WebSite",
                "@id":ORIGIN+"/#website","name":"ZazoomTek","url":ORIGIN+"/",
                "inLanguage":"it-IT","publisher":{"@id":ORIGIN+"/#organization"}})
    elif "BreadcrumbList" not in seen:
        h = Heading()
        h.feed(remainder)
        heading = " ".join(" ".join(h.parts).split())
        if not heading or len(heading) > 240:
            return source
        path_name = path.name
        parent = next((v for prefix, v in CATEGORY.items() if path_name.startswith(prefix)), None)
        if not parent and path_name in ARCHIVE:
            parent = None
        elif not parent:
            # No category guessing for arbitrary articles.
            return source
        crumbs = [{"@type":"ListItem","position":1,"name":"Home","item":ORIGIN+"/"}]
        if parent:
            label, filename = parent
            crumbs.append({"@type":"ListItem","position":2,"name":label,"item":ORIGIN+"/"+filename})
        crumbs.append({"@type":"ListItem","position":len(crumbs)+1,"name":heading,"item":canonical})
        new.append({"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":crumbs})
    if not new:
        return source
    block = "\n" + MARKER + "\n" + "\n".join(
        '<script type="application/ld+json">'+json.dumps(item,ensure_ascii=False,separators=(",",":")).replace("<","\\u003c")+'</script>'
        for item in new) + "\n"
    output = head + block + remainder
    assert output.endswith(remainder)
    return output

def build(root):
    root = root.resolve()
    pages = list(html_pages(root))
    if len(pages) < 500:
        raise RuntimeError("Unusually small site snapshot; abort Schema.org enrichment")
    edits = {}
    for path in pages:
        original = path.read_text(encoding="utf-8")
        revised = transform(path, root, original)
        if revised != original:
            edits[path] = revised
    return edits, len(pages)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    edits, count = build(args.root)
    for path, revised in edits.items():
        if not args.check:
            path.write_text(revised, encoding="utf-8")
    print(f"Schema.org completion: {len(edits)} eligible pages / {count} checked; dry-run={args.check}")

if __name__ == "__main__":
    main()
