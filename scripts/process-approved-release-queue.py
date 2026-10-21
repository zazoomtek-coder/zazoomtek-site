#!/usr/bin/env python3
"""Owner-approved pull-request queue: merge at its assigned editorial slot only.

An approved preview in a PR cannot be deployed until it reaches main. This
script closes that gap. It never triggers Cloudflare, bypasses no build gates,
and runs only inside scheduled Master workflow with authenticated permissions.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "editorial/approved-release-queue.json"
SLOTS = {
    "15 10,15,20 * * *": ((10, 15), (15, 15), (20, 15)),
    "45 12,17 * * *": ((12, 45), (17, 45)),
}


def due_items(data: dict, now: datetime, event_cron: str) -> list[dict]:
    if event_cron not in SLOTS and event_cron != "manual-approved":
        raise ValueError("Not a configured editorial release event")
    if now.tzinfo is None:
        raise ValueError("Timezone-aware clock required")
    # Event origin is authenticated by process() (schedule + GitHub Actions).
    # A runner starting late must still process every previously approved item
    # whose publication time has passed; a real scheduled run never expires.
    if data.get("version") != 1 or not isinstance(data.get("items"), list):
        raise ValueError("Invalid editorial approval queue")
    due, seen = [], set()
    for item in data["items"]:
        if not isinstance(item, dict):
            raise ValueError("Malformed queue item")
        number, sha = item.get("pr"), item.get("head_sha")
        at = datetime.fromisoformat(str(item.get("publish_at", "")))
        if (not isinstance(number, int) or number <= 0 or number in seen or
                not isinstance(sha, str) or not re.fullmatch("[a-f0-9]{40}", sha) or
                at.tzinfo is None or item.get("owner_approved") is not True or
                at.utcoffset() != at.astimezone(ZoneInfo("Europe/Rome")).utcoffset()):
            raise ValueError("PR entry needs valid Rome time, SHA and owner approval")
        seen.add(number)
        if at <= now:
            due.append(item)
    return sorted(due, key=lambda x: x["publish_at"])


def cli(*args: str) -> str:
    proc = subprocess.run(args, capture_output=True, text=True,
                          check=True, timeout=90)
    return proc.stdout.strip()


def process(now: datetime, cron: str, *, dry_run: bool) -> None:
    data = json.loads(QUEUE.read_text(encoding="utf-8"))
    items = due_items(data, now, cron)
    repo = os.getenv("GITHUB_REPOSITORY", "")
    event = os.getenv("GITHUB_EVENT_NAME")
    authorized_event = (event == "schedule" and cron in SLOTS) or (cron == "manual-approved" and event in ("push", "workflow_dispatch"))
    if not dry_run and (not authorized_event or
                        os.getenv("GITHUB_ACTIONS") != "true" or
                        not os.getenv("GH_TOKEN") or
                        not re.fullmatch(r"[\w.-]+/[\w.-]+", repo)):
        raise RuntimeError("Approved PR merges require authenticated scheduled or explicit manual Master event")
    print(f"EDITORIAL QUEUE: {len(items)} approved PR(s) due in this window", flush=True)
    for entry in items:
        pr, pin = entry["pr"], entry["head_sha"]
        if dry_run:
            print(f"EDITORIAL QUEUE DRY-RUN: #{pr}, SHA {pin[:12]}")
            continue
        # Failures remain pending and are retried in the next scheduled window.
        # Transient GitHub failures get two additional attempts in this run.
        for attempt in range(1, 4):
            try:
                info = json.loads(cli("gh", "pr", "view", str(pr), "--repo", repo,
                                      "--json", "state,headRefOid,baseRefName,isDraft"))
                if info["state"] == "MERGED":
                    print(f"EDITORIAL QUEUE: #{pr} already merged")
                    break
                if (info["state"] != "OPEN" or info["isDraft"] or
                        info["baseRefName"] != "main" or info["headRefOid"] != pin):
                    print(f"::warning::EDITORIAL QUEUE: #{pr} differs from "
                          "the editor-approved revision; retain for reapproval", flush=True)
                    break
                cli("gh", "pr", "merge", str(pr), "--repo", repo, "--squash",
                    "--match-head-commit", pin)
                print(f"EDITORIAL QUEUE: merged #{pr} at its approved slot", flush=True)
                break
            except (subprocess.SubprocessError, OSError, ValueError, KeyError) as exc:
                # Never allow one failed PR to block the remaining approved queue.
                print(f"::warning::EDITORIAL QUEUE: #{pr} attempt {attempt}/3 "
                      f"failed: {str(exc)[:320]}", flush=True)
                if attempt == 3:
                    print(f"::warning::EDITORIAL QUEUE: #{pr} retained for "
                          "the next editorial slot", flush=True)


def self_test() -> None:
    t = datetime.fromisoformat("2026-10-21T12:46:00+02:00")
    data = {"version": 1, "items": [
        {"pr": 119, "head_sha": "a"*40,
         "publish_at": "2026-10-21T12:45:00+02:00", "owner_approved": True},
        {"pr": 118, "head_sha": "b"*40,
         "publish_at": "2026-10-22T10:15:00+02:00", "owner_approved": True},
    ]}
    assert [x["pr"] for x in due_items(data, t, "45 12,17 * * *")] == [119]
    assert [x["pr"] for x in due_items(data, t, "manual-approved")] == [119]
    # A delayed scheduled event must not strand an approved backlog.
    delayed = datetime.fromisoformat("2026-10-21T15:40:00+02:00")
    assert [x["pr"] for x in due_items(data, delayed, "45 12,17 * * *")] == [119]
    assert not due_items(data, datetime.fromisoformat("2026-10-21T10:16:00+02:00"),
                         "15 10,15,20 * * *")
    try:
        due_items(data, t, "2-57/5 11-19 * * *")
    except ValueError:
        pass
    else:
        raise AssertionError("Never publish on five-minute poll")
    data["items"][0]["owner_approved"] = False
    try:
        due_items(data, t, "45 12,17 * * *")
    except ValueError:
        pass
    else:
        raise AssertionError("Unapproved PR must not enter publication queue")
    print("PASS: approved PR only at its own editorial window; no early publish")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--cron", default="")
    args = p.parse_args()
    if args.self_test:
        self_test()
    else:
        process(datetime.now(ZoneInfo("Europe/Rome")), args.cron, dry_run=args.dry_run)
