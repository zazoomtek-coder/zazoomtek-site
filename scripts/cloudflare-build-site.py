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
    # Re-evaluate freshness offline at build time; 4h portal checks remain separate.
    # Never publish an expired card while waiting for the next curator run.
    run("trending-crosscheck.py", "--apply")
    run("cloudflare-sync-featured-home.py")
    # Mandatory offline regression gate: fail BEFORE any Cloudflare Pages build.
    run("test-featured-today-yesterday.py")
    run("verify-editorial-home.py")
    # Public video pages are HTML with YouTube embeds, not downloaded movies.
    run("seo_watch_pages_safe.py")
    run("zt_sidebar_mix.py")
    run("build-related-content.py")
    # Cross-check review article titles against genuine full-length review
    # videos in the verified ZazoomTek YouTube catalog. No unverified links.
    run("link-review-videos.py")
    run("verify-review-video-links.py")
    run("build-cloudflare-pages.py")
    output = ROOT / "dist"
    assert (output / "watch" / "index.html").is_file()
    assert (output / "news.html").is_file()
    # Public receipt written ONLY after every editorial and artifact check
    # succeeded. Used by GitHub to verify actual Cloudflare production.
    import json
    import re
    from datetime import datetime, timezone
    release_file = ROOT / "cloudflare-release-trigger.txt"
    marker = release_file.read_text(encoding="utf-8")
    match = re.search(r"^source_commit=([a-f0-9]{40})$", marker, re.M)
    if not match:
        raise RuntimeError("Cloudflare release source SHA is missing or invalid")
    receipt = {
        "source_commit": match.group(1),
        "validated": True,
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (output / "zt-release-status.json").write_text(
        json.dumps(receipt, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8")
    print("CLOUDFLARE SITE READY; release receipt:", match.group(1), flush=True)

if __name__ == "__main__":
    main()
