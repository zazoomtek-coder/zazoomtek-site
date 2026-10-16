#!/usr/bin/env python3
"""One-command, offline Cloudflare Pages production build for ZazoomTek.

Run on Cloudflare (not on readers' browsers). Rebuild approved design, reviews,
YouTube iframe watch pages and related sidebars from already-published sources.
No Firebase, third-party news scraping, video downloading or live API keys.
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def run(script: str, *args: str) -> None:
    print("CLOUDFLARE BUILD:", script, " ".join(args), flush=True)
    subprocess.run([sys.executable, str(ROOT / "scripts" / script), *args],
                   cwd=ROOT, check=True, timeout=180)

def main() -> None:
    run("validate-sync-output.py", "community")
    run("validate-sync-output.py", "videos")
    run("refresh-home-latest-reviews.py")
    run("apply-site-design.py")
    # The curator edits JSON, not Home. Apply approved 5 Tech + 1 Gaming here.
    run("cloudflare-sync-featured-home.py")
    # Public video pages are HTML with YouTube embeds, not downloaded movies.
    run("seo_watch_pages_safe.py")
    run("zt_sidebar_mix.py")
    run("build-related-content.py")
    run("build-cloudflare-pages.py")
    output = ROOT / "dist"
    assert (output / "watch" / "index.html").is_file()
    assert (output / "news.html").is_file()
    print("CLOUDFLARE SITE READY; all operations were build-time only.", flush=True)

if __name__ == "__main__":
    main()
