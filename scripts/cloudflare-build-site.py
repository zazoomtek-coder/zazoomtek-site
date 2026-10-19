#!/usr/bin/env python3
"""One-command, offline Cloudflare Pages production build for ZazoomTek.

Run on Cloudflare (not on readers' browsers). Rebuild approved design, reviews,
YouTube iframe watch pages and related sidebars from already-published sources.
No Firebase, third-party news scraping, video downloading or live API keys.
"""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def run(script: str, *args: str) -> None:
    print("CLOUDFLARE BUILD:", script, " ".join(args), flush=True)
    subprocess.run([sys.executable, str(ROOT / "scripts" / script), *args],
                   cwd=ROOT, check=True, timeout=180)

def main() -> None:
    # Refuse unauthorized Home structural changes before any publication.
    run("verify-home-layout-lock.py")
    # Master production mode: all content is derived from verified JSON.
    # The generated markup is temporary Cloudflare build output, never
    # a write to the tracked Home/layout source by a data importer.
    import json
    flag = ROOT / "master-production-enabled.json"
    master_active = (flag.is_file() and
                     json.loads(flag.read_text(encoding="utf-8")).get("enabled") is True)
    # This test flag only works for a PR validation and is never a production
    # switch. A reviewer must verify JSON->HTML parity before the real cutover.
    if os.environ.get("GITHUB_EVENT_NAME") == "pull_request" and os.environ.get("ZT_MASTER_STAGING_TEST") == "1":
        master_active = True
    if master_active:
        # The Cloudflare build is a fresh environment, independent of GitHub
        # Actions. Guarantee the same image-rendering dependency here, otherwise
        # the first live build could fail despite staging green.
        try:
            from PIL import Image
            assert Image is not None
        except ImportError:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--quiet",
                 "--disable-pip-version-check", "Pillow>=10,<13"],
                cwd=ROOT, check=True, timeout=180,
            )
        # Approved ordinary NEWS are generated only in temporary Cloudflare
        # build workspace; their approved JSON remains the Git source of truth.
        run("build-standard-news.py")
        run("apply-standard-news-featured.py")
        run("update-youtube-posts.py", "--render-from-cache")
        if (ROOT / ".youtube-master-render-cache.json").is_file():
            run("update-youtube.py", "--render-from-cache")
        # Editor-approved Impact/Inside pages and category archives share
        # this same disposable build; no independent Git writer survives cutover.
        run("publish-special-news.py")
        run("master-json-renderer.py", "--prebuild-reviews")
        run("verify-home-layout-lock.py")
    run("test_home_10x10_release.py")
    run("validate-sync-output.py", "community")
    run("validate-sync-output.py", "videos")
    run("refresh-home-latest-reviews.py")
    # Category lists are prebuilt; readers never scan or filter review content.
    run("build-review-categories.py")
    # Studio-approved Tech/Gaming long-form SPECIALI, no runtime filtering.
    run("build-speciali.py")
    run("apply-site-design.py")
    # Add original ISO times ONLY to already-published archive cards; safe even
    # when the YouTube importer skips a cycle with no new Community posts.
    run("enrich-news-archive-publication-times.py")
    # Refresh rankings from already published ZazoomTek news; portal checks are separate.
    # Never expire existing verified cards just because no new post was published.
    run("trending-crosscheck.py", "--apply")
    run("cloudflare-sync-featured-home.py")
    # Mandatory offline regression gate: fail BEFORE any Cloudflare Pages build.
    run("test-featured-today-yesterday.py")
    run("test-cloudflare-featured-home.py")
    run("verify-editorial-home.py")
    # Public video pages are HTML with YouTube embeds, not downloaded movies.
    run("seo_watch_pages_safe.py")
    run("zt_sidebar_mix.py")
    run("build-related-content.py")
    # Cross-check review article titles against genuine full-length review
    # videos in the verified ZazoomTek YouTube catalog. No unverified links.
    run("link-review-videos.py")
    run("verify-review-video-links.py")
    # Normalize existing and future written review pages with a factual
    # summary and a 16:9 thumbnail. Never touch the locked Home layout.
    run("ensure-review-summaries.py")
    run("ensure-review-summaries.py", "--check")
    # Generators may refresh content, but must never rewrite locked Home layout.
    run("verify-home-layout-lock.py")
    run("build-cloudflare-pages.py")
    if master_active and (ROOT / "master-staging/editorial-boxes.json").is_file():
        run("master-json-renderer.py", "--postbuild-editorial")
    run("verify-home-layout-lock.py", "--packaged")
    run("test_home_10x10_release.py", "dist")
    run("verify-packaged-home.py", "--root", "dist")
    output = ROOT / "dist"
    assert (output / "watch" / "index.html").is_file()
    assert (output / "news.html").is_file()
    assert (output / "studio/index.html").is_file()
    assert (output / "studio/publisher.js").is_file()
    assert (output / "studio/layouts.js").is_file()
    assert (output / "studio/template-news.html").is_file()
    assert (output / "studio/template-review.html").is_file()
    assert (output / "speciali.html").is_file()
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
