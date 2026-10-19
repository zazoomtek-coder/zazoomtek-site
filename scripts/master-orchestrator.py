#!/usr/bin/env python3
"""ZazoomTek master pipeline -- safe JSON-only staging, no commits to main or deploy.

Legacy importers run inside disposable detached Git worktrees. Only approved
JSON files can leave a module sandbox. This is deliberately NOT a production
publisher: HTML-based legacy importers need data/render separation before cutover.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Callable
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = ["tech", "tech", "tech", "tech", "gaming"]
PROTECTED = (
    "index.html", "zt-design.css", "zt-visual.js", "firebase.json",
    "studio/publisher.js", "studio/layouts.js",
    "zt-home-live.js",
    "zt-home-graphic-layout-20261016.css",
    "zt-home-graphic-layout-20261016.js",
    "zt-home-gap-fix-20261014.css",
)
NAV_LINKS = (
    "/recensioni-tech.html", "/recensioni-gaming.html",
    "/tech-today.html", "/gaming-today.html", "/speciali.html",
)


def command(cwd: Path, *argv: str, timeout: int = 360) -> str:
    try:
        result = subprocess.run(argv, cwd=cwd, check=True, text=True,
                                capture_output=True, timeout=timeout)
        return (result.stdout + result.stderr).strip()
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"TIMEOUT after {timeout}s: {argv[0]} {argv[1] if len(argv)>1 else ''}") from error
    except subprocess.CalledProcessError as error:
        detail = ((error.stdout or "") + "\n" + (error.stderr or ""))[-1500:]
        raise RuntimeError(f"Command failed (exit {error.returncode}): {detail}") from error


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(root: Path) -> dict[str, str]:
    return {name: digest(root / name) for name in PROTECTED}


def verify_source(root: Path, baseline: dict[str, str]) -> None:
    for name, original in baseline.items():
        if not (root / name).is_file() or digest(root / name) != original:
            raise RuntimeError("BLOCK: protected HTML/CSS/JS changed: " + name)
    command(root, sys.executable, "scripts/verify-home-layout-lock.py", timeout=90)
    home = (root / "index.html").read_text(encoding="utf-8")
    match = re.search(r'<nav\b[^>]*class="nav"[^>]*>(.*?)</nav>', home, re.I | re.S)
    if not match or any(f'href="{href}"' not in match.group() for href in NAV_LINKS):
        raise RuntimeError("BLOCK: canonical Home navigation missing links")
    for href in NAV_LINKS:
        if not (root / href[1:]).is_file():
            raise RuntimeError("BLOCK: missing navigation page " + href)


def verify_sitewide_nav(root: Path) -> int:
    """Current menu (two dropdowns) rather than the obsolete nine-item check."""
    header = re.compile(r"<header\b[^>]*>[\s\S]*?</header>", re.I)
    nav = re.compile(r'<nav\b[^>]*class="nav"[^>]*>(.*?)</nav>', re.I | re.S)
    count = 0
    for page in sorted(root.glob("*.html")):
        if page.name.startswith(("preview-", "anteprima-", "audit-", "test-")):
            continue
        source = page.read_text(encoding="utf-8", errors="replace")
        h = header.search(source)
        if not h or not any(x in h.group().upper() for x in ("ZAZOOM", "CHATGPT.PNG")):
            continue
        n = nav.search(h.group())
        if not n:
            raise RuntimeError(f"Missing sitewide menu on {page.name}")
        if n.group().count('class="nav-drop-trigger"') != 2:
            raise RuntimeError(f"Missing two navigation dropdowns on {page.name}")
        if any(f'href="{link}"' not in n.group() for link in NAV_LINKS):
            raise RuntimeError(f"Missing submenu links on {page.name}")
        if "zt-unified-header.js" in source:
            raise RuntimeError(f"Obsolete async menu on {page.name}")
        count += 1
    if count < 50:
        raise RuntimeError(f"Too few validated editorial pages: {count}")
    return count


def validate_featured(root: Path, item: dict) -> None:
    url, image, title = item.get("url"), item.get("image"), item.get("title")
    if (not isinstance(url, str) or not re.fullmatch(r"/news-[A-Za-z0-9_-]+\.html", url)
            or not (root / url[1:]).is_file()):
        raise ValueError("Invalid or missing featured article: " + str(url))
    if not isinstance(title, str) or len(title.strip()) < 12:
        raise ValueError("Missing featured article title: " + str(url))
    if not isinstance(image, str) or not image.startswith(("https://", "/assets/")):
        raise ValueError("Invalid featured image: " + str(url))
    if image.startswith("/assets/") and not (root / image[1:]).is_file():
        raise ValueError("Missing local featured image: " + str(image))
    try:
        publication = date.fromisoformat(item["published_date"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Missing valid featured article date: " + str(url)) from exc
    if publication > datetime.now(ZoneInfo("Europe/Rome")).date():
        raise ValueError("Future-dated featured article: " + str(url))


def five_slot_manifest(root: Path) -> dict:
    """4 TECH + 1 GAMING exactly; Specials remain in their editorial boxes."""
    content = json.loads((root / "featured-carousel.json").read_text(encoding="utf-8"))
    items = content.get("items")
    if not isinstance(items, list) or len(items) != 5 or not all(isinstance(x, dict) for x in items):
        raise ValueError("Carousel must contain exactly 5 ordinary news")
    sections = [x.get("section") for x in items]
    if sections != EXPECTED or Counter(sections) != Counter({"tech": 4, "gaming": 1}):
        raise ValueError("Carousel slots must be 4 Tech then 1 Gaming")
    for item in items:
        validate_featured(root, item)
        title=item["title"].lower()
        if (re.search(r"\b(?:iscritt[io]|followers?|subscriber[s]?|traguardo)\b", title)
                and re.search(r"(?:zazoomtek|nostr[oaie]|canale|community|youtube)", title)):
            raise ValueError("Community subscriber celebration cannot occupy a Tech innovation slot")
    if len({item["url"] for item in items}) != 5:
        raise ValueError("Duplicate article in carousel")
    keys = ("section", "url", "title", "image", "published_date")
    return {"mode": "STAGING_ONLY", "layout_unchanged": True,
            "policy": "4-tech-1-gaming", "items": [{k: x[k] for k in keys} for x in items]}


def self_test() -> None:
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        items = []
        for i, category in enumerate(EXPECTED):
            url = f"/news-demo-{i}.html"
            (root / url[1:]).write_text("<html>Demo</html>", encoding="utf-8")
            items.append({"section": category, "url": url, "title": f"Verified demo news {i}",
                          "image": "https://example.org/cover.png", "published_date": "2026-10-19"})
        state = root / "featured-carousel.json"
        state.write_text(json.dumps({"items": items}), encoding="utf-8")
        assert [x["section"] for x in five_slot_manifest(root)["items"]] == EXPECTED
        assert len(five_slot_manifest(root)["items"]) == 5
        for wrong in [items[:4], items + [items[0]]]:
            state.write_text(json.dumps({"items": wrong}), encoding="utf-8")
            try:
                five_slot_manifest(root)
            except ValueError:
                pass
            else:
                raise AssertionError("Incorrect carousel length accepted")
        items[1]["url"] = items[0]["url"]
        state.write_text(json.dumps({"items": items}), encoding="utf-8")
        try:
            five_slot_manifest(root)
        except ValueError:
            pass
        else:
            raise AssertionError("Duplicate carousel accepted")
    print("PASS: carousel exactly 5, four Tech + one Gaming; rejected partial/duplicate feeds")


def json_bytes(path: Path) -> bytes:
    payload = path.read_bytes()
    if not payload or len(payload) > 8_000_000:
        raise ValueError(f"Invalid JSON data size: {path.name}")
    obj = json.loads(payload.decode("utf-8"))
    if not isinstance(obj, (list, dict)) or not obj:
        raise ValueError(f"Empty or malformed JSON: {path.name}")
    return payload


def checkpoint(root: Path, scope: tuple[str, ...], label: str) -> None:
    if not scope:
        return
    command(root, "git", "add", "--", *scope)
    changed = command(root, "git", "diff", "--cached", "--name-only")
    allowed = set(scope)
    if any(name not in allowed or not name.endswith(".json") for name in changed.splitlines()):
        raise RuntimeError("BLOCK: attempted non-data commit")
    if changed:
        command(root, "git", "-c", "user.name=ZT Staging", "-c",
                "user.email=staging@users.noreply.github.com",
                "commit", "-m", f"staging-json-only: {label}")


def rollback(root: Path) -> None:
    command(root, "git", "reset", "--hard", "HEAD")
    command(root, "git", "clean", "-fd")


def stage(root: Path, baseline: dict[str, str], records: list[dict], name: str,
          action: Callable[[Path], None], allowed_data: tuple[str, ...] = (),
          mandatory: bool = False) -> bool:
    """Each legacy module runs in ITS OWN disposable worktree; transfer JSON only.

    No HTML/CSS/JS emitted by a legacy importer can reach our staging state.
    Failed modules preserve their previous JSON and do not stop later modules.
    A mandatory failure still blocks final approval/deploy.
    """
    with tempfile.TemporaryDirectory(prefix="zt-module-") as scratch:
        module_root = Path(scratch) / "module"
        command(ROOT, "git", "worktree", "add", "--detach", str(module_root),
                command(root, "git", "rev-parse", "HEAD"), timeout=120)
        try:
            action(module_root)
            transferred = {}
            for relative in allowed_data:
                if not relative.endswith(".json") or ".." in Path(relative).parts:
                    raise RuntimeError("Invalid data scope: " + relative)
                file = module_root / relative
                if file.is_file():
                    contents = json_bytes(file)
                    destination = root / relative
                    if not destination.exists() or destination.read_bytes() != contents:
                        transferred[relative] = contents
            changed = command(module_root, "git", "status", "--porcelain", "--untracked-files=normal")
            legacy_html = any(".html" in row or ".css" in row or ".js " in row for row in changed.splitlines())
            for rel, raw in transferred.items():
                dest = root / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(raw)
            verify_source(root, baseline)
            if name == "trending-carousel":
                five_slot_manifest(root)
            checkpoint(root, tuple(transferred), name)
            records.append({"module": name, "status": "ok", "json_updated": sorted(transferred),
                            "legacy_html_discarded": legacy_html})
            return True
        except Exception as exc:
            rollback(root)
            records.append({"module": name, "status": "fallback-last-good", "error": str(exc)[-1200:]})
            if mandatory:
                raise RuntimeError(f"BLOCK: required module {name}: {exc}") from exc
            return False
        finally:
            command(ROOT, "git", "worktree", "remove", "--force", str(module_root), timeout=120)


def exec_module(script: str, *extra: str, timeout: int = 360) -> Callable[[Path], None]:
    return lambda folder: command(folder, sys.executable, "scripts/" + script, *extra, timeout=timeout)


def reports_from_dryrun(script: str, output: str) -> Callable[[Path], None]:
    """Legacy HTML renderer runs DRY: output only a JSON editorial queue."""
    def run(folder: Path) -> None:
        raw = command(folder, sys.executable, "scripts/" + script, "--dry-run", timeout=180)
        data = json.loads(raw)
        path = folder / "master-staging" / output
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return run


def save_summary(output: Path, status: str, records: list[dict]) -> None:
    failed = [s["module"] for s in records if s["status"] == "fallback-last-good"]
    # HTML generated in the disposable BUILD is the expected JSON->site output,
    # not an unsafe importer. Only data-stage HTML indicates a missing adapter.
    discarded = [s["module"] for s in records
                 if s.get("legacy_html_discarded")
                 and s["module"] != "isolated-offline-build"]
    summary = {
        "status": status, "mode": "staging-only-no-push-no-deploy",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "carosello": "5 slot: 4 Tech + 1 Gaming",
        "protected_source_html_css_js_unchanged": True,
        "legacy_rendering_requires_json_adapters": bool(discarded),
        "modules_with_fallback": failed,
        "production_deploy_allowed": False,
        "old_workflows_unchanged": True,
        "modules": records,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "report.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def run(args: argparse.Namespace) -> int:
    target = Path(args.output_dir).resolve()
    target.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    status = "blocked"
    with tempfile.TemporaryDirectory(prefix="zt-master-") as scratch:
        source = Path(scratch) / "source"
        command(ROOT, "git", "worktree", "add", "--detach", str(source), "HEAD", timeout=120)
        try:
            original_commit = command(source, "git", "rev-parse", "HEAD")
            baseline = snapshot(source)
            verify_source(source, baseline)
            records.append({"module": "preflight-home-css-nav", "status": "ok"})
            steps = [
                ("youtube-community", exec_module("update-youtube-posts.py", timeout=360),
                 (".youtube-posts.json",), args.with_imports),
                ("youtube-videos", exec_module("update-youtube.py", timeout=240),
                 (".youtube-latest.json", "home-video-feed.json", ".youtube-master-render-cache.json"),
                 args.with_imports and bool(os.getenv("YOUTUBE_API_KEY"))),
                ("video-watch-archive", exec_module("seo_video_archive_safe.py", timeout=90),
                 ("video-watch-archive.json",), True),
                ("approved-reviews", reports_from_dryrun("publish-approved-reviews.py", "reviews-due.json"),
                 ("master-staging/reviews-due.json",), True),
                ("trending-scan", exec_module("trending-crosscheck.py", "--sources", timeout=240),
                 ("trending-sources.json",), args.with_imports),
                ("trending-carousel", exec_module("trending-crosscheck.py", "--apply", timeout=120),
                 ("featured-carousel.json", "trending-match-report.json"), True),
                ("editorial-boxes", reports_from_dryrun("refresh-home-editorial-boxes.py", "editorial-boxes.json"),
                 ("master-staging/editorial-boxes.json",), True),
            ]
            for name, operation, files, enabled in steps:
                if enabled:
                    stage(source, baseline, records, name, operation, files)
                else:
                    records.append({"module": name, "status": "skipped-in-test"})
            stage(source, baseline, records, "five-slot-carousel",
                  lambda folder: (folder / "master-staging").mkdir(parents=True, exist_ok=True)
                    or (folder / "master-staging/carousel-five.json").write_text(
                        json.dumps(five_slot_manifest(folder), ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8"),
                  ("master-staging/carousel-five.json",), mandatory=True)
            # Production-equivalent rendering occurs in its OWN throwaway worktree,
            # never in the JSON-only parent source worktree.
            def build_preview(folder: Path) -> None:
                # Data acquisition writes JSON only. Rendering is a separate,
                # reversible phase inside THIS disposable build worktree.
                command(folder, sys.executable, "scripts/master-json-renderer.py",
                        "--prebuild-reviews", timeout=180)
                community = next((x for x in records if x["module"] == "youtube-community"), {})
                if community.get("status") == "ok" and ".youtube-posts.json" in community.get("json_updated", []):
                    command(folder, sys.executable, "scripts/update-youtube-posts.py",
                            "--render-from-cache", timeout=600)
                videos = next((x for x in records if x["module"] == "youtube-videos"), {})
                if videos.get("status") == "ok" and ".youtube-master-render-cache.json" in videos.get("json_updated", []):
                    command(folder, sys.executable, "scripts/update-youtube.py",
                            "--render-from-cache", timeout=600)
                if args.simulate_production_render and os.getenv("GITHUB_EVENT_NAME") == "pull_request":
                    os.environ["ZT_MASTER_STAGING_TEST"] = "1"
                try:
                    command(folder, sys.executable, "scripts/cloudflare-build-site.py", timeout=900)
                finally:
                    os.environ.pop("ZT_MASTER_STAGING_TEST", None)
                if (folder / "master-staging/editorial-boxes.json").is_file():
                    command(folder, sys.executable, "scripts/master-json-renderer.py",
                            "--postbuild-editorial", timeout=180)
                command(folder, sys.executable, "scripts/verify-home-layout-lock.py", "--packaged", timeout=90)
                command(folder, sys.executable, "scripts/verify-packaged-home.py", "--root", "dist", timeout=90)
                verify_sitewide_nav(folder / "dist")
                shutil.copytree(folder / "dist", target / "preview-site", dirs_exist_ok=True)
            stage(source, baseline, records, "isolated-offline-build", build_preview, mandatory=True)
            verify_source(source, baseline)
            (target / "carousel-five.json").write_text(
                json.dumps(five_slot_manifest(source), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8")
            if args.export_json_dir:
                # DATA-ONLY handoff to the separate production gateway.
                # Export everything committed by successful import modules,
                # never any generated layout, CSS, JS, media or HTML.
                dest = Path(args.export_json_dir).resolve()
                dest.mkdir(parents=True, exist_ok=True)
                changes = command(source, "git", "diff", "--name-only",
                                  original_commit, "HEAD").splitlines()
                paths = sorted(set(x for x in changes if x.endswith(".json")))
                if len(paths) != len(set(changes)):
                    raise RuntimeError("Non-JSON production export prohibited")
                allowed = {
                    ".youtube-posts.json", ".youtube-latest.json",
                    ".youtube-master-render-cache.json", "home-video-feed.json",
                    "featured-carousel.json", "trending-match-report.json",
                    "trending-sources.json", "master-staging/reviews-due.json",
                    "master-staging/editorial-boxes.json",
                    "master-staging/carousel-five.json",
                }
                if any(x not in allowed for x in paths):
                    raise RuntimeError("Unexpected production export file: " + str(paths))
                for relative in paths:
                    file = source / relative
                    if not file.is_file():
                        raise RuntimeError("Missing approved JSON export: " + relative)
                    payload = json_bytes(file)
                    target_file = dest / relative
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    target_file.write_bytes(payload)
                (dest / "manifest.json").write_text(
                    json.dumps({"paths": paths, "base_commit": original_commit},
                               ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            status = ("staging-validated-with-fallbacks" if any(x["status"] == "fallback-last-good" for x in records)
                      else "staging-validated")
        except Exception as exc:
            records.append({"module": "pipeline", "status": "blocked", "error": str(exc)[-1200:]})
        finally:
            command(ROOT, "git", "worktree", "remove", "--force", str(source), timeout=120)
    save_summary(target, status, records)
    return 1 if status == "blocked" else 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--simulate-production-render", action="store_true", help="CI-only, test Cloudflare JSON→HTML renderer without arming production")
    parser.add_argument("--with-imports", action="store_true",
                        help="Explicitly test external YouTube/portal feeds, still no deploy")
    parser.add_argument("--output-dir", default="artifacts/master-orchestrator")
    parser.add_argument("--export-json-dir", help="Export only validated JSON for guarded production gateway")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    sys.exit(run(args))


if __name__ == "__main__":
    main()
