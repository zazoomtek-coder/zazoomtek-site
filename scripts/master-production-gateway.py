#!/usr/bin/env python3
"""Sole Git/Cloudflare publisher AFTER atomic cutover; fail-closed until enabled.

The source of truth is validated JSON. Cloudflare builds HTML from those data
files; this program never publishes an unvalidated layout or Cloudflare build.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "master-production-enabled.json"
ALLOWED = {
    ".youtube-posts.json", ".youtube-latest.json", ".youtube-master-render-cache.json",
    "home-video-feed.json", "featured-carousel.json", "trending-match-report.json",
    "trending-sources.json", "video-watch-archive.json", "master-staging/reviews-due.json",
    "master-staging/editorial-boxes.json", "master-staging/carousel-five.json",
}


class ReleaseBlocked(RuntimeError):
    pass


def call(*args: str, cwd: Path = ROOT, timeout: int = 1200) -> str:
    try:
        p = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                           check=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise ReleaseBlocked(f"Timed out: {args[:2]}") from exc
    except subprocess.CalledProcessError as exc:
        raise ReleaseBlocked(f"{args[:2]} failed: {(exc.stdout + exc.stderr)[-1700:]}") from exc
    return (p.stdout + p.stderr).strip()


def enabled() -> bool:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    return isinstance(config, dict) and config.get("enabled") is True


def audit_cutover() -> dict:
    from importlib.util import spec_from_file_location, module_from_spec
    spec = spec_from_file_location("zt_master_cutover_audit", ROOT / "scripts/master-cutover-audit.py")
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    status = module.report(ROOT)
    if not status["cutover_ready"]:
        raise ReleaseBlocked(
            "Competing GitHub writers are still active. No publisher cutover: " +
            ", ".join(status["blockers"][:8]))
    return status


def preflight() -> None:
    if not enabled():
        raise ReleaseBlocked("Production is not explicitly armed; no Git or Cloudflare changes")
    if os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise ReleaseBlocked("Only main may publish")
    key=os.environ.get("YOUTUBE_API_KEY", "")
    if not key or key.startswith(chr(92)) or "${{" in key:
        raise ReleaseBlocked("YouTube secret missing/escaped: do not degrade the import pipeline")
    audit_cutover()
    if call("git", "status", "--porcelain"):
        raise ReleaseBlocked("Checkout contains uncommitted files")
    call(sys.executable, "scripts/verify-home-layout-lock.py", timeout=90)
    call(sys.executable, "scripts/cloudflare-release-control.py", "--self-test", timeout=90)
    call(sys.executable, "scripts/verify-live-cloudflare.py", "--self-test", timeout=60)


def import_and_validate(folder: Path) -> list[str]:
    export = folder / "json"
    result_dir = folder / "staging"
    call(sys.executable, "scripts/master-orchestrator.py", "--with-imports",
         "--output-dir", str(result_dir), "--export-json-dir", str(export), timeout=2100)
    report = json.loads((result_dir / "report.json").read_text(encoding="utf-8"))
    if report.get("status") != "staging-validated":
        raise ReleaseBlocked("Master has errors/fallbacks; KEEP LAST GOOD LIVE")
    required = ("youtube-community", "youtube-videos", "video-watch-archive", "trending-carousel",
                "editorial-boxes", "approved-reviews", "isolated-offline-build")
    stages = {x["module"]: x for x in report.get("modules", [])}
    if any(stages.get(x, {}).get("status") != "ok" for x in required):
        raise ReleaseBlocked("Required importer was skipped or failed; stop publication")
    manifest = json.loads((export / "manifest.json").read_text(encoding="utf-8"))
    names = manifest.get("paths")
    if not isinstance(names, list) or any(x not in ALLOWED for x in names):
        raise ReleaseBlocked("Unapproved data file in master export")
    for name in names:
        original = export / name
        if not original.is_file() or original.is_symlink():
            raise ReleaseBlocked("Missing/malformed exported JSON: " + name)
        payload = json.loads(original.read_text(encoding="utf-8"))
        if not isinstance(payload, (dict, list)) or not payload:
            raise ReleaseBlocked("Empty/corrupt JSON: " + name)
        target = ROOT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, target)
    return names


def one_attempt() -> tuple[bool, str]:
    """No remote mutation until the full preview/build and SHA checks succeed."""
    call("git", "fetch", "origin", "main", timeout=120)
    call("git", "checkout", "main", timeout=90)
    call("git", "reset", "--hard", "origin/main", timeout=90)
    initial = call("git", "rev-parse", "HEAD")
    preflight()
    with tempfile.TemporaryDirectory(prefix="zt-production-") as tmp:
        names = import_and_validate(Path(tmp))
    if names:
        call("git", "add", "--", *names)
        if call("git", "diff", "--cached", "--name-only"):
            call("git", "-c", "user.name=ZazoomTek Master",
                 "-c", "user.email=actions@users.noreply.github.com",
                 "commit", "-m", "master: verified JSON-only editorial batch")
    # A release trigger is necessary ONLY at the existing controlled window,
    # and exactly one extra Git commit lets it contain the real source SHA.
    call(sys.executable, "scripts/cloudflare-release-control.py", "--scheduled-slot", timeout=120)
    trigger_changed = bool(call("git", "status", "--porcelain", "--", "cloudflare-release-trigger.txt"))
    trigger_source = ""
    if trigger_changed:
        marker = (ROOT / "cloudflare-release-trigger.txt").read_text(encoding="utf-8")
        match = re.search(r"(?m)^source_commit=([a-f0-9]{40})$", marker)
        if not match:
            raise ReleaseBlocked("Missing release receipt SHA")
        trigger_source = match.group(1)
        # The build is checked in the run before any push; Pages should watch
        # the trigger only. Its own build must also pass or remain last good.
        call(sys.executable, "scripts/cloudflare-build-site.py", timeout=1500)
        call("git", "add", "--", "cloudflare-release-trigger.txt")
        call("git", "-c", "user.name=ZazoomTek Master",
             "-c", "user.email=actions@users.noreply.github.com",
             "commit", "-m", "master: one verified Cloudflare release request")
    if call("git", "rev-parse", "HEAD") == initial:
        return False, ""
    # Never rebase locally generated release receipts across concurrent edits.
    # Re-run all import/validation from a fresh main if anything changed.
    call("git", "fetch", "origin", "main", timeout=120)
    if call("git", "rev-parse", "origin/main") != initial:
        raise ReleaseBlocked("Main moved during validation; reject stale push and rerun")
    # No force pushes. Any racing write is handled by the outer retry.
    call("git", "push", "origin", "HEAD:main", timeout=180)
    return trigger_changed, trigger_source


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--check-cutover", action="store_true")
    ap.add_argument("--publish", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        assert len(ALLOWED) == len(set(ALLOWED))
        assert all(x.endswith(".json") for x in ALLOWED)
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        assert config.get("enabled") is False, "Do not accidentally arm staging"
        print("PASS: JSON allowlist and release is disarmed by default")
        return
    if args.check_cutover:
        preflight()
        print("PASS: no competing GitHub writers, release gate armed")
        return
    if not args.publish:
        ap.error("Choose --self-test, --check-cutover or --publish")
    last = None
    for attempt in range(1, 4):
        try:
            published, source = one_attempt()
            print(json.dumps({"success": True, "release_requested": published,
                              "source_commit": source}, ensure_ascii=False))
            if published:
                call(sys.executable, "scripts/verify-live-cloudflare.py",
                     "--source-commit", source,
                     "--timeout-seconds", "840", timeout=890)
                print("VERIFIED: public Cloudflare release matches master source", flush=True)
            return
        except ReleaseBlocked as exc:
            last = exc
            print(f"Attempt {attempt}/3 blocked safely: {exc}", file=sys.stderr, flush=True)
            # A new external main commit may explain a rejected push. Retrying is
            # safe, but NEVER force-push or bypass the validation/release gate.
            if attempt < 3 and ("Main moved" in str(exc) or "git', 'push" in str(exc)):
                continue
            break
    raise SystemExit("BLOCKED: " + str(last) + ". Last good site remains online.")


if __name__ == "__main__":
    main()
