#!/usr/bin/env python3
"""ZazoomTek Master Orchestrator - isolated STAGING / DRY-RUN only.

Calls the existing site importers one at a time in a disposable Git worktree.
All intermediate commits are LOCAL checkpoints; neither main nor Cloudflare is
changed. Later production adoption requires a separate, reviewed release gate.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PROTECTED = (
    "zt-design.css", "zt-visual.js", "firebase.json",
    "studio/publisher.js", "studio/layouts.js",
    "zt-home-graphic-layout-20261016.css",
    "zt-home-graphic-layout-20261016.js",
    "zt-home-gap-fix-20261014.css",
)
NAV_DESTINATIONS = (
    "/recensioni-tech.html", "/recensioni-gaming.html",
    "/tech-today.html", "/gaming-today.html", "/speciali.html",
)


def command(cwd: Path, *args: str, timeout: int = 360) -> str:
    completed = subprocess.run(args, cwd=cwd, check=True, text=True,
                               capture_output=True, timeout=timeout)
    return (completed.stdout + completed.stderr)[-1800:]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_snapshot(root: Path) -> dict[str, str]:
    return {name: digest(root / name) for name in PROTECTED}


def validate_core(root: Path, baseline: dict[str, str]) -> None:
    for name, expected in baseline.items():
        if not (root / name).is_file() or digest(root / name) != expected:
            raise RuntimeError(f"Protected file changed: {name}")
    command(root, sys.executable, "scripts/verify-home-layout-lock.py", timeout=90)
    home = (root / "index.html").read_text(encoding="utf-8")
    nav = re.search(r'<nav\b[^>]*class="nav"[^>]*>(.*?)</nav>', home, re.S | re.I)
    if not nav or any(f'href="{target}"' not in nav.group(1) for target in NAV_DESTINATIONS):
        raise RuntimeError("Canonical Home navigation or review/special destinations missing")
    for target in NAV_DESTINATIONS:
        if not (root / target.lstrip("/")).is_file():
            raise RuntimeError(f"Navigation destination is missing: {target}")


def validate_link(root: Path, item: dict) -> None:
    url, cover, title = (item.get("url"), item.get("image"), item.get("title"))
    if (not isinstance(url, str) or not re.fullmatch(r"/[A-Za-z0-9_.-]+\.html", url)
            or not (root / url.lstrip("/")).is_file()):
        raise ValueError(f"Missing or unsafe carousel URL: {url}")
    if not isinstance(title, str) or len(title.strip()) < 12:
        raise ValueError(f"Carousel title missing for {url}")
    if not isinstance(cover, str) or not (cover.startswith("https://") or cover.startswith("/assets/")):
        raise ValueError(f"Invalid carousel cover: {url}")
    if cover.startswith("/assets/") and not (root / cover.lstrip("/")).is_file():
        raise ValueError(f"Carousel cover not found: {cover}")


def six_slot_manifest(root: Path) -> dict:
    """Staging ONLY: 4 Tech + 1 Gaming + 1 Special, NEVER overwrite live 5-card UI."""
    current = json.loads((root / "featured-carousel.json").read_text(encoding="utf-8"))
    ordinary = current.get("items")
    if (not isinstance(ordinary, list) or len(ordinary) != 5
            or Counter(x.get("section") for x in ordinary if isinstance(x, dict)) !=
               Counter({"tech": 4, "gaming": 1})):
        raise ValueError("Last-good carousel must have exactly 4 Tech + 1 Gaming")
    specials = json.loads((root / "special-featured.json").read_text(encoding="utf-8")).get("items", [])
    last_good = []
    for x in ordinary:
        validate_link(root, x)
        last_good.append({k: x[k] for k in ("section", "url", "title", "image", "published_date")})
    for special in specials:
        if not isinstance(special, dict):
            continue
        slug = special.get("slug", "")
        section = ("tech-impact" if slug.startswith("tech-impact-") else
                   "gaming-inside" if slug.startswith("gaming-inside-") else None)
        if not section:
            continue
        candidate = {"section": section, "url": "/" + slug,
                     "title": special.get("title"), "image": special.get("image")}
        try:
            validate_link(root, candidate)
        except ValueError:
            continue
        if candidate["url"] not in {a["url"] for a in last_good}:
            items = last_good + [candidate]
            if len(items) != 6 or len({a["url"] for a in items}) != 6:
                raise ValueError("Carousel contains duplicate links")
            return {"mode": "STAGING_ONLY", "layout_unchanged": True,
                    "policy": "4-tech-1-gaming-1-special", "items": items}
    raise ValueError("Neither Tech Impact nor Gaming Inside has a valid special article")


def self_test() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        items = []
        for n, section in enumerate(["tech"] * 4 + ["gaming"]):
            url = f"/news-test-{n}.html"
            (root / url.lstrip("/")).write_text("<html>news</html>", encoding="utf-8")
            items.append({"section": section, "url": url, "title": "Test editorial article",
                          "image": "https://example.org/cover.jpg", "published_date": "2026-10-19"})
        (root / "featured-carousel.json").write_text(json.dumps({"items": items}), encoding="utf-8")
        special = "tech-impact-example.html"
        (root / special).write_text("<html>special</html>", encoding="utf-8")
        (root / "special-featured.json").write_text(json.dumps({"items": [{"slug": special,
            "title": "Test special editorial article", "image": "https://example.org/cover.jpg"}]}), encoding="utf-8")
        assert [x["section"] for x in six_slot_manifest(root)["items"]] == ["tech"] * 4 + ["gaming", "tech-impact"]
        (root / special).unlink()
        try:
            six_slot_manifest(root)
        except ValueError:
            pass
        else:
            raise AssertionError("Broken special link must never create a six-card manifest")
    print("PASS: six-slot staging logic, category quotas, no duplicates, missing-link fallback")


def checkpoint(root: Path, name: str) -> None:
    command(root, "git", "add", "-A")
    status = command(root, "git", "diff", "--cached", "--name-only")
    if status.strip():
        command(root, "git", "-c", "user.name=ZT Staging", "-c",
                "user.email=staging@users.noreply.github.com", "commit", "-m", f"local-checkpoint: {name}")


def rollback(root: Path) -> None:
    # Only operates inside a disposable, detached worktree; NEVER on main.
    command(root, "git", "reset", "--hard", "HEAD")
    command(root, "git", "clean", "-fd")


def stage(root: Path, baseline: dict[str, str], report: list[dict], name: str,
          action, *, optional: bool = True) -> bool:
    try:
        action()
        validate_core(root, baseline)
        checkpoint(root, name)
        report.append({"module": name, "status": "ok"})
        return True
    except Exception as exc:
        rollback(root)
        report.append({"module": name, "status": "fallback-last-good", "reason": str(exc)[:400]})
        if not optional:
            raise RuntimeError(f"Required stage {name} failed: {exc}") from exc
        return False


def run(args: argparse.Namespace) -> int:
    target = Path(args.output_dir).resolve()
    target.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    manifest = None
    outcome = "blocked"
    # Worktree is detached at the workflow's checked-out commit. Legacy bots may
    # continue writing main; this test cannot race with or publish to that branch.
    with tempfile.TemporaryDirectory(prefix="zt-master-") as temp:
        work = Path(temp) / "site"
        command(ROOT, "git", "worktree", "add", "--detach", str(work), "HEAD", timeout=120)
        try:
            baseline = protected_snapshot(work)
            validate_core(work, baseline)
            results.append({"module": "preflight-home-css-nav", "status": "ok"})
            stages = [
                ("youtube-community", [sys.executable, "scripts/update-youtube-posts.py"], 360, args.with_imports),
                ("youtube-videos", [sys.executable, "scripts/update-youtube.py"], 240,
                 args.with_imports and bool(os.getenv("YOUTUBE_API_KEY"))),
                ("approved-reviews", [sys.executable, "scripts/publish-approved-reviews.py"], 150, True),
                ("trending-source-scan", [sys.executable, "scripts/trending-crosscheck.py", "--sources"],
                 240, args.with_imports),
                ("trending-five-card-source", [sys.executable, "scripts/trending-crosscheck.py", "--apply"], 120, True),
                ("home-editorial-boxes", [sys.executable, "scripts/refresh-home-editorial-boxes.py"], 160, True),
            ]
            for name, cmd, timeout, enabled in stages:
                if not enabled:
                    results.append({"module": name, "status": "skipped-offline-or-missing-key"})
                    continue
                stage(work, baseline, results, name,
                      lambda cmd=cmd, timeout=timeout: command(work, *cmd, timeout=timeout))
            candidate = work / "master-staging" / "carousel-six.json"
            def prepare_carousel() -> None:
                nonlocal manifest
                manifest = six_slot_manifest(work)
                candidate.parent.mkdir(parents=True, exist_ok=True)
                candidate.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            stage(work, baseline, results, "six-slot-carousel-isolated", prepare_carousel, optional=False)
            # Cloudflare's CURRENT renderer and validators still require five cards.
            # Do not alter them in a staging experiment; the sixth slot has no live effect.
            def build() -> None:
                command(work, sys.executable, "scripts/cloudflare-build-site.py", timeout=900)
                validate_core(work, baseline)
                command(work, sys.executable, "scripts/verify-home-layout-lock.py", "--packaged", timeout=90)
                command(work, sys.executable, "scripts/verify-packaged-home.py", "--root", "dist", timeout=90)
                command(work, sys.executable, "scripts/test_sitewide_home_header.py", "--root", "dist", timeout=90)
            stage(work, baseline, results, "production-equivalent-build", build, optional=False)
            shutil.copytree(work / "dist", target / "preview-site", dirs_exist_ok=True)
            if manifest:
                (target / "carousel-six.json").write_text(
                    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            outcome = "staging-validated"
        except Exception as exc:
            results.append({"module": "pipeline", "status": "blocked", "reason": str(exc)[:600]})
        finally:
            command(ROOT, "git", "worktree", "remove", "--force", str(work), timeout=90)
    report = {"status": outcome, "mode": "test-only-no-push-no-deploy",
              "created_utc": datetime.now(timezone.utc).isoformat(), "modules": results,
              "live_carousel_unchanged": True, "live_workflows_unchanged": True}
    (target / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if outcome == "staging-validated" else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--with-imports", action="store_true",
                        help="Explicit manual staging run with network importers")
    parser.add_argument("--output-dir", default="artifacts/master-orchestrator")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    raise SystemExit(run(args))


if __name__ == "__main__":
    main()
