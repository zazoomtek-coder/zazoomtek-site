#!/usr/bin/env python3
"""Verify the newly published editorial pages on the actual production domain.

A successful Wrangler upload alone is not proof that an article is public.
On failure this exits nonzero so the release receipt is NOT stamped.
"""
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://zazoomtek.it"
TODAY = datetime.now(ZoneInfo("Europe/Rome")).date().isoformat()


def rows(filename, key):
    return json.loads((ROOT / "data" / filename).read_text(encoding="utf-8"))[key]


def targets():
    chosen = []
    for row in rows("studio_posts.json", "posts"):
        if row.get("date") == TODAY and row.get("slug"):
            chosen.append((row["slug"], row["title"]))
    for row in rows("community_imported.json", "posts"):
        if row.get("date") == TODAY and row.get("id") and row.get("title"):
            slug = "community-" + re.sub(r"[^a-z0-9]+", "-", row["id"].lower()).strip("-")
            chosen.append((slug, row["title"]))
    return list(dict(((slug, title) for slug, title in chosen)).items())


def main():
    sitemap = (ROOT / "dist/sitemap.xml").read_text(encoding="utf-8")
    locs = [n.text or "" for n in ET.fromstring(sitemap).iter() if n.tag.rsplit("}", 1)[-1] == "loc"]
    selected = targets()
    if not selected:
        print("LIVE CHECK: no articles dated today; skipping targeted page checks")
        return 0
    problems = []
    urls = []
    for slug, title in selected:
        matched = [html.unescape(u) for u in locs
                   if urlparse(html.unescape(u)).path.rstrip("/").split("/")[-1] == slug]
        if len(matched) != 1:
            problems.append(f"Article missing or ambiguous in built sitemap: {slug}")
        else:
            urls.append((matched[0], title))
            if not (ROOT / "dist" / (slug + ".html")).is_file():
                problems.append(f"Article missing in built site: {slug}")
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    # Local assets must exist before checking the public site.\n    for row in rows("studio_posts.json", "posts"):\n        if row.get("date") != TODAY:\n            continue\n        asset = str(row.get("image") or "")\n        if asset.startswith("/assets/uploads/") and not (ROOT / "dist" / asset.lstrip("/")).is_file():\n            problems.append(f"Missing published Studio cover: {asset}")\n    if problems:\n        print("\\n".join(problems), file=sys.stderr)\n        return 1\n    for attempt in range(1, 7):
        pending = []
        for url, title in urls:
            try:
                req = urllib.request.Request(url, headers={
                    "User-Agent": "ZazoomTek-Editorial-Release-Check/1.0",
                    "Cache-Control": "no-cache",
                })
                with urllib.request.urlopen(req, timeout=18) as response:
                    page = response.read().decode("utf-8", errors="replace")
                    status = response.status
                # Verify the actual title, not merely a 200 response or a fallback page.
                display_title = re.sub(r"^\s*(?:News|Review|Recensione)(?:\s+(?:Tech|Gaming|Extra))?\s*:\s*", "", title, flags=re.I)
                marker = html.escape(display_title[:45], quote=False)
                if status != 200 or (display_title[:45] not in html.unescape(page)
                                     and marker not in page):
                    pending.append(url + " (missing article title)")
            except (OSError, urllib.error.URLError, ValueError) as exc:
                pending.append(url + " (" + str(exc)[:120] + ")")
        if not pending:
            print(f"LIVE VERIFIED: {len(urls)} today's Studio/YouTube articles on {BASE}")
            return 0
        print(f"LIVE CHECK attempt {attempt}/6: {len(pending)} unavailable", flush=True)
        if attempt < 6:
            time.sleep(10)
    print("PUBLICATION NOT CONFIRMED:\n" + "\n".join(pending), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
