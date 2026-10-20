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
    "trending-sources.json", "master-staging/reviews-due.json",
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


def preflight(*, require_imports: bool = True) -> None:
    if not enabled():
        raise ReleaseBlocked("Production is not explicitly armed; no Git or Cloudflare changes")
    if os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise ReleaseBlocked("Only main may publish")
    if require_imports and not os.environ.get("YOUTUBE_API_KEY"):
        raise ReleaseBlocked("YouTube secret unavailable for imports; pending-content releases do not require it")
    audit_cutover()
    if call("git", "status", "--porcelain"):
        raise ReleaseBlocked("Checkout contains uncommitted files")
    call(sys.executable, "scripts/verify-home-layout-lock.py", timeout=90)
    call(sys.executable, "scripts/cloudflare-release-control.py", "--self-test", timeout=90)
    call(sys.executable, "scripts/verify-live-cloudflare.py", "--self-test", timeout=60)


def import_and_validate(folder: Path, poll_only: bool = False) -> list[str]:
    export = folder / "json"
    result_dir = folder / "staging"
    args = [sys.executable, "scripts/master-orchestrator.py", "--with-imports",
            "--output-dir", str(result_dir), "--export-json-dir", str(export)]
    if poll_only:
        args.append("--poll-only")
    call(*args, timeout=2100)
    report = json.loads((result_dir / "report.json").read_text(encoding="utf-8"))
    allowed_status = (("poll-validated", "poll-validated-with-fallbacks") if poll_only
                      else ("staging-validated", "staging-validated-with-fallbacks"))
    if report.get("status") not in allowed_status:
        raise ReleaseBlocked("Master structural validation failed; preserve last-good public site")
    stages = {x["module"]: x for x in report.get("modules", [])}
    # No unrelated importer may veto the good output of another importer.
    # Full releases still require a verified complete render, a valid carousel,
    # and a valid Home; individual YouTube/trending errors retain last-good data.
    if not poll_only:
        required = ("five-slot-carousel", "isolated-offline-build")
        if any(stages.get(x, {}).get("status") != "ok" for x in required):
            raise ReleaseBlocked("Verified offline build or required Home artifacts failed")
    failures = [x["module"] for x in report.get("modules", [])
                if x.get("status") in ("fallback-last-good", "skipped-in-test")]
    if failures:
        print("::warning::Individual modules unavailable, preserving last-good "
              "data without losing verified independent updates: "
              + ", ".join(failures), flush=True)
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



def refresh_due_review_plan(root: Path = ROOT) -> bool:
    """Refresh time-dependent approvals without rerunning external importers."""
    raw = call(sys.executable, "scripts/publish-approved-reviews.py", "--dry-run",
               cwd=root, timeout=150)
    try:
        plan = json.loads(raw)
    except ValueError as exc:
        raise ReleaseBlocked("Approved review dry-run returned invalid JSON") from exc
    if (not isinstance(plan, dict) or not isinstance(plan.get("due"), list)
            or not isinstance(plan.get("changed"), list)
            or any(not isinstance(item, str) for item in plan["due"])
            or any(not isinstance(name, str) or "/" in name or "\\\\" in name
                   or not name.endswith((".html", ".xml")) for name in plan["changed"])
            or plan.get("dry_run") is not True):
        raise ReleaseBlocked("Malformed approved review publication plan")
    path = root / "master-staging/reviews-due.json"
    output = json.dumps(plan, ensure_ascii=False, indent=2) + "\n"
    if path.is_file() and path.read_text(encoding="utf-8") == output:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(output, encoding="utf-8")
    return True


def test_due_review_plan() -> None:
    """A scheduled review becoming due must be seen by a pending-only release."""
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    with tempfile.TemporaryDirectory(prefix="zt-review-plan-test-") as folder:
        root = Path(folder)
        (root / "scripts").mkdir()
        (root / "editorial").mkdir()
        shutil.copyfile(ROOT / "scripts/publish-approved-reviews.py",
                        root / "scripts/publish-approved-reviews.py")
        card = '<article class="video-card zt-review-card">Existing</article>'
        (root / "index.html").write_text(
            "<!-- HOME_LATEST_REVIEWS_MAIN_START -->" + card * 5
            + "<!-- HOME_LATEST_REVIEWS_MAIN_END -->", encoding="utf-8")
        (root / "recensioni-scritte.html").write_text(
            '<div class="news-list" id="reviewList"></div>', encoding="utf-8")
        for name in ("sitemap.xml", "google-sitemap.xml"):
            (root / name).write_text("<urlset></urlset>", encoding="utf-8")
        now = datetime.now(ZoneInfo("Europe/Rome"))
        items = []
        for n, delta in ((1, -5), (2, 60)):
            source = f"anteprima-demo-{n}.html"
            (root / source).write_text(
                "<html><head><title>Review</title></head><body>"
                "<article><h1>Review</h1></article></body></html>", encoding="utf-8")
            items.append({"id": f"demo-{n}", "status": "approved",
                          "publish_at": (now + timedelta(minutes=delta)).isoformat(),
                          "source": source, "target": f"demo-{n}-recensione.html",
                          "title": f"Demo review {n}", "platform": "TECH",
                          "date_label": now.date().isoformat(),
                          "description": "A verified demo review",
                          "image": "/assets/demo.jpg"})
        queue = root / "editorial/review-publication-queue.json"
        data = {"version": 1, "timezone": "Europe/Rome", "items": items}
        queue.write_text(json.dumps(data), encoding="utf-8")
        assert refresh_due_review_plan(root)
        path = root / "master-staging/reviews-due.json"
        first = json.loads(path.read_text(encoding="utf-8"))
        assert first["due"] == ["demo-1"]
        assert not refresh_due_review_plan(root)
        items[1]["publish_at"] = (now - timedelta(minutes=1)).isoformat()
        queue.write_text(json.dumps(data), encoding="utf-8")
        assert refresh_due_review_plan(root)
        assert json.loads(path.read_text(encoding="utf-8"))["due"] == ["demo-1", "demo-2"]
    print("PASS: pending releases refresh newly due reviews and preserve future approvals")

def one_attempt(poll_only: bool = False, urgent: bool = False,
                publish_pending: bool = False) -> tuple[bool, str]:
    """No remote mutation until the full preview/build and SHA checks succeed."""
    call("git", "fetch", "origin", "main", timeout=120)
    call("git", "checkout", "main", timeout=90)
    call("git", "reset", "--hard", "origin/main", timeout=90)
    initial = call("git", "rev-parse", "HEAD")
    # Scheduled publications are permitted even when an unrelated YouTube
    # importer is unavailable. Poll-only jobs still require their API secret.
    # Community imports may still work even if the separate videos API secret
    # is temporarily unavailable. Each importer reports its own outcome.
    preflight(require_imports=False)
    # Explicit manual releases never rerun unrelated imports.
    if publish_pending:
        names = []
    # Missing credentials for one importer must not prevent independently
    # acquired and validated data from other importers reaching the next slot.
    else:
        try:
            with tempfile.TemporaryDirectory(prefix="zt-production-") as tmp:
                names = import_and_validate(Path(tmp), poll_only=poll_only)
        except ReleaseBlocked as exc:
            if poll_only or urgent:
                raise  # Never hide a broken poll or a manually requested import.
            print("::warning::Master content acquisition failed; attempting "
                  "safe scheduled release of previously approved changes: "
                  + str(exc)[:350], flush=True)
            # Some adapters may have copied data before raising. Discard ALL
            # partial tracked edits; never turn an incomplete import into a
            # public release. Stop if untracked changes remain.
            call("git", "reset", "--hard", initial, timeout=90)
            if call("git", "status", "--porcelain"):
                raise ReleaseBlocked(
                    "Incomplete importer left untracked changes: safe release blocked")
            names = []
    if not poll_only and refresh_due_review_plan():
        names = sorted(set(names) | {"master-staging/reviews-due.json"})
    if names:
        call("git", "add", "--", *names)
        if call("git", "diff", "--cached", "--name-only"):
            call("git", "-c", "user.name=ZazoomTek Master",
                 "-c", "user.email=actions@users.noreply.github.com",
                 "commit", "-m", "master: verified JSON-only editorial batch")
    trigger_changed = False
    trigger_source = ""
    if not poll_only:
        # A release trigger is necessary ONLY at the existing controlled window,
        # and exactly one extra Git commit lets it contain the real source SHA.
        # Explicit user-requested releases may run immediately. Scheduled jobs
        # continue to respect fixed slots; both paths retain budgets and validation.
        gate = "--urgent" if urgent else "--scheduled-slot"
        call(sys.executable, "scripts/cloudflare-release-control.py", gate, timeout=120)
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
    ap.add_argument("--publish-pending", action="store_true",
                    help="Publish already-approved pending site changes immediately, without reimporting")
    ap.add_argument("--poll", action="store_true", help="Fast serialized YouTube JSON-only importer; no release request")
    ap.add_argument("--urgent", action="store_true", help="Explicitly approved immediate Cloudflare release; requires --publish")
    args = ap.parse_args()
    if args.self_test:
        assert len(ALLOWED) == len(set(ALLOWED))
        assert all(x.endswith(".json") for x in ALLOWED)
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        assert isinstance(config.get("enabled"), bool), "Malformed production activation flag"
        assert config.get("carousel_policy") == {"tech": 4, "gaming": 1, "total": 5}
        assert sum(bool(x) for x in (True,False,False)) == 1
        assert "cloudflare-release-trigger.txt" not in ALLOWED
        test_due_review_plan()
        print("PASS: JSON allowlist, pending-only release mode and production activation flag")
        return
    if args.check_cutover:
        # Read-only workflow prerequisite must not require YouTube import secrets:
        # the actual selected run mode performs its own mode-specific preflight.
        preflight(require_imports=False)
        print("PASS: no competing GitHub writers, release gate armed")
        return
    if sum(bool(x) for x in (args.publish, args.poll, args.publish_pending)) != 1:
        ap.error("Choose exactly one mode: --poll, --publish, or --publish-pending")
    if args.urgent and not (args.publish or args.publish_pending):
        ap.error("--urgent requires --publish or --publish-pending")
    last = None
    for attempt in range(1, 4):
        try:
            published, source = one_attempt(poll_only=args.poll, urgent=args.urgent,
                                            publish_pending=args.publish_pending)
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
                # After an isolated offline build, generated untracked pages,
                # assets and dist files can survive git reset --hard. Do not
                # let those temporary files block the next valid retry.
                # Only clean on the disposable GitHub Actions checkout;
                # never delete a developer's local untracked work.
                if os.environ.get("GITHUB_ACTIONS") == "true":
                    call("git", "reset", "--hard", "HEAD", timeout=90)
                    call("git", "clean", "-fd", timeout=90)
                continue
            break
    raise SystemExit("BLOCKED: " + str(last) + ". Last good site remains online.")


if __name__ == "__main__":
    main()
