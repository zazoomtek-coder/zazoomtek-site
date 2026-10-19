#!/usr/bin/env python3
"""Produce a Cloudflare Pages-ready static snapshot without changing source files.
Only editorial/media assets go to dist. Never deploy scripts or Firebase services.
"""
from __future__ import annotations
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist"
ALLOWED = {".html", ".css", ".js", ".json", ".xml", ".txt", ".svg",
           ".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico", ".avif",
           ".woff", ".woff2", ".pdf"}
SKIP_FILES = {"comments.js", "comments.css", "commenti-policy.html",
              "firebase.json", "firestore.rules"}
SKIP_PREFIXES = ("preview-", "anteprima-", "audit-", "test-", "check-")
SKIP_DIRS = {".github", "scripts", "functions", "editorial", "includes",
             "node_modules", ".git", "dist"}
MAX_FILES = 19000
MAX_FILE_BYTES = 25 * 1024 * 1024

def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, check=True, stdout=subprocess.PIPE)
    published = [Path(os.fsdecode(name)) for name in result.stdout.split(b"\0") if name]
    # Watch pages are produced at build time, not stored or synced as videos.
    # Include only the verified HTML player pages, never media bytes.
    generated_watch = list((ROOT / "watch").glob("*.html")) if (ROOT / "watch").is_dir() else []
    return published + [p.relative_to(ROOT) for p in generated_watch]

def eligible(path: Path) -> bool:
    parts = path.parts
    if any(part.startswith(".") or part in SKIP_DIRS for part in parts):
        return False
    if path.name in SKIP_FILES or path.name.startswith(SKIP_PREFIXES):
        return False
    if path.suffix.lower() not in ALLOWED:
        return False
    # Keep site pages, public metadata and web media; exclude automation data.
    # Studio is a standalone publishing interface; permit only its reviewed
    # fixed reviewed files. Never ship local drafts or build-only support files.
    if len(parts) > 1 and parts[0] == "studio":
        return len(parts) == 2 and path.name in {"index.html", "publisher.js", "layouts.js", "template-news.html", "template-review.html"}
    if len(parts) > 1 and parts[0] not in ("assets", "watch"):
        return False
    if path.name.endswith(("-report.json", "-state.json", "-manifest.json")):
        return False
    return True

def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    files = [p for p in tracked_files() if eligible(p)]
    failures = []
    for path in files:
        src = ROOT / path
        if not src.is_file():
            continue
        if src.stat().st_size > MAX_FILE_BYTES:
            failures.append(f"{path}: larger than 25 MiB")
            continue
        dest = OUT / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    copied = [p for p in OUT.rglob("*") if p.is_file()]
    if len(copied) > MAX_FILES:
        failures.append(f"{len(copied)} files exceed safety margin of {MAX_FILES}")
    for required in ("index.html", "news.html", "robots.txt", "sitemap.xml",
                     "zt-design.css", "zt-home-live.js", "featured-carousel.json"):
        if not (OUT / required).is_file():
            failures.append("Missing core public file: " + required)
    if not (OUT / "watch/index.html").is_file():
        failures.append("Missing verified YouTube video player directory")
    # A Studio release must never contain an HTML shell without its JS publisher.
    for studio_file in ("studio/index.html", "studio/publisher.js", "studio/layouts.js", "studio/template-news.html", "studio/template-review.html"):
        if not (OUT / studio_file).is_file():
            failures.append("Missing Studio online editor file: " + studio_file)
    # If an editorial review is in the repository, it must reach the public
    # snapshot with its cover, full page, and official review archive link.
    review_slug = "thermomate-2500w-recensione-riscaldatore-infrarossi-2-in-1.html"
    if (ROOT / review_slug).is_file():
        review_page = OUT / review_slug
        review_cover = OUT / "assets/recensioni/thermomate-2500w/cover.webp"
        review_archive = OUT / "recensioni-scritte.html"
        if not review_page.is_file() or not review_cover.is_file():
            failures.append("ThermoMate review or cover missing from Cloudflare artifact")
        if (review_archive.is_file()
                and review_slug not in review_archive.read_text(encoding="utf-8")):
            failures.append("ThermoMate review missing from official archive")
        if review_page.is_file():
            reviewed = review_page.read_text(encoding="utf-8")
            if "Voto finale" not in reviewed and "8.5/10" not in reviewed:
                failures.append("ThermoMate full review/vote missing from Cloudflare artifact")

    # SPECIALI must be a complete static page with shared layout/assets.
    specials = OUT / "speciali.html"
    if not specials.is_file():
        failures.append("Missing public SPECIALI archive")
    else:
        special_html = specials.read_text(encoding="utf-8")
        for marker in ('id="specialiList"', "zt-mix-feature", "zt-mix-recent",
                       'class="news-sidebar', "/zt-design.css", "/zt-visual.js",
                       "https://zazoomtek.it/speciali.html"):
            if marker not in special_html:
                failures.append("Incomplete public SPECIALI page: " + marker)

    # Verify actual featured articles and local images are delivered.
    try:
        import json
        featured = json.loads((OUT / "featured-carousel.json").read_text(encoding="utf-8"))
        chosen = featured.get("items", [])
        if (not isinstance(chosen, list) or len(chosen)!=5 or
                [x.get("section") for x in chosen]!=["tech"]*4+["gaming"] or
                len({x["url"] for x in chosen})!=5):
            failures.append("Invalid featured manifest: require 4 Tech + 1 Gaming, unique real cards")
        for item in chosen:
            for field in ("url", "image"):
                value = item.get(field, "")
                if not isinstance(value, str) or not value:
                    failures.append("Featured card missing " + field)
                elif value.startswith("/") and not (OUT / value.lstrip("/")).is_file():
                    failures.append("Missing featured " + field + ": " + value)
    except (OSError, ValueError, TypeError, KeyError) as err:
        failures.append("Cannot validate featured carousel: " + str(err))
    # No copied videos: YouTube remains responsible for storage and streaming.
    if any(p.suffix.lower() in (".mp4", ".webm", ".mov", ".mkv") for p in copied):
        failures.append("Video bytes detected in static Cloudflare output")
    # Build-only secrets and automation must NEVER become public assets.
    for forbidden in ("functions", "scripts", ".github", "firebase.json",
                      "comments.js", "comments.css", "firestore.rules"):
        if (OUT / forbidden).exists():
            failures.append("Private/retired resource unexpectedly public: " + forbidden)
    # Do not cache editorial feeds or content HTML. Static media can be cached.
    (OUT / "_headers").write_text(
        "/*.html\n  Cache-Control: public, max-age=0, must-revalidate\n"
        "/\n  Cache-Control: public, max-age=0, must-revalidate\n"
        "/*.json\n  Cache-Control: public, max-age=0, must-revalidate\n"
        "/*.xml\n  Cache-Control: public, max-age=0, must-revalidate\n"
        "/*.js\n  Cache-Control: public, max-age=0, must-revalidate\n"
        "/*.css\n  Cache-Control: public, max-age=0, must-revalidate\n"
        "/assets/*\n  Cache-Control: public, max-age=86400\n",
        encoding="utf-8")
    if failures:
        for problem in failures:
            print("FAIL:", problem, file=sys.stderr)
        raise SystemExit(1)
    print(f"PASS: Cloudflare snapshot contains {len(copied)} public files; "
          f"{sum(p.stat().st_size for p in copied)/1024/1024:.1f} MiB; "
          "no comment backend or internal scripts.")
if __name__ == "__main__":
    main()
