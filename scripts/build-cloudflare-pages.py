#!/usr/bin/env python3
"""Produce a Cloudflare Pages-ready static snapshot without changing source files.
Only editorial/media assets go to dist. Never deploy scripts or Firebase services.
"""
from __future__ import annotations
import os
import json
import re
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

def generated_approved_files() -> set[Path]:
    """Safelist ONLY pages and media generated from authoritative editorial JSON.

    Static Cloudflare builds need to include newly rendered news/reviews even
    though the Master publisher itself commits JSON, never the generated HTML.
    Arbitrary untracked HTML and drafts are NOT exposed.
    """
    config = ROOT / "master-production-enabled.json"
    active = (config.is_file() and
              json.loads(config.read_text(encoding="utf-8")).get("enabled") is True)
    staging = (os.getenv("GITHUB_EVENT_NAME") == "pull_request"
               and os.getenv("ZT_MASTER_STAGING_TEST") == "1")
    if not active and not staging:
        return set()
    generated: set[Path] = set()

    def add(relative: str) -> None:
        target = Path(relative.lstrip("/"))
        if not target.is_absolute() and ".." not in target.parts and eligible(target):
            if (ROOT / target).is_file():
                generated.add(target)

    community = ROOT / ".youtube-posts.json"
    if community.is_file():
        posts = json.loads(community.read_text(encoding="utf-8"))
        if not isinstance(posts, list) or len(posts) < 20:
            raise ValueError("Invalid Community inventory for generated Cloudflare pages")
        for post in posts:
            if not isinstance(post, dict):
                continue
            identifier = post.get("id")
            if isinstance(identifier, str) and re.fullmatch(r"[A-Za-z0-9_-]{8,80}", identifier):
                for prefix in ("news-", "recensione-", "tech-impact-", "gaming-inside-"):
                    add(prefix + identifier + ".html")

    ordinary = ROOT / "standard-news.json"
    if ordinary.is_file():
        rows = json.loads(ordinary.read_text(encoding="utf-8")).get("articles", [])
        for article in rows:
            slug = article.get("slug")
            if not isinstance(slug, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
                # Skip an invalid metadata row without preventing other
                # approved generated articles from reaching the package.
                print("::warning::Skipping invalid standard NEWS slug in artifact inventory", flush=True)
                continue
            add("news-" + slug + ".html")
            add("assets/special/news-" + slug + ".webp")
            add("assets/special/article-" + slug + ".webp")

    special = ROOT / "approved-special-articles.json"
    if special.is_file():
        rows = json.loads(special.read_text(encoding="utf-8")).get("articles", [])
        for article in rows:
            slug = article.get("slug")
            prefix = {"tech": "tech-impact-", "gaming": "gaming-inside-"}.get(article.get("section"))
            if (prefix and isinstance(slug, str)
                    and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug)
                    and (article.get("editor_approved") is True or article.get("auto_approved") is True)):
                add(prefix + slug + ".html")
                cover = article.get("image", "")
                if isinstance(cover, str) and cover.startswith("/assets/"):
                    add(cover)

    # Generated archive pages are safe only when named sequentially by the approved builder.
    for page in ROOT.glob("cybercultura-*.html"):
        if re.fullmatch(r"cybercultura-[2-9][0-9]*\.html",page.name):
            add(page.name)

    reviews = ROOT / "editorial/review-publication-queue.json"
    if reviews.is_file():
        queue = json.loads(reviews.read_text(encoding="utf-8"))
        items = queue.get("items", []) if isinstance(queue, dict) else []
        for item in items:
            if not isinstance(item, dict) or item.get("status") != "approved":
                continue
            target = item.get("target")
            if isinstance(target, str) and re.fullmatch(r"[A-Za-z0-9_-]+\.html", target):
                add(target)
    return generated


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, check=True, stdout=subprocess.PIPE)
    published = {Path(os.fsdecode(name)) for name in result.stdout.split(b"\0") if name}
    # Video watch pages use only official YouTube iframes, never media bytes.
    generated_watch = {p.relative_to(ROOT) for p in (ROOT / "watch").glob("*.html")} if (ROOT / "watch").is_dir() else set()
    return sorted(published | generated_watch | generated_approved_files(), key=str)

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
