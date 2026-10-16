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
           ".woff", ".woff2", ".mp4", ".webm", ".pdf"}
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
    return [Path(os.fsdecode(name)) for name in result.stdout.split(b"\0") if name]

def eligible(path: Path) -> bool:
    parts = path.parts
    if any(part.startswith(".") or part in SKIP_DIRS for part in parts):
        return False
    if path.name in SKIP_FILES or path.name.startswith(SKIP_PREFIXES):
        return False
    if path.suffix.lower() not in ALLOWED:
        return False
    # Keep site pages, public metadata and web media; exclude automation data.
    if len(parts) > 1 and parts[0] != "assets":
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
