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
    if event_cron not in SLOTS:
        raise ValueError("Not a configured editorial release event")
    if now.tzinfo is None:
        raise ValueError("Timezone-aware clock required")
    local = now.astimezone(ZoneInfo("Europe/Rome"))
    starts = [local.replace(hour=h, minute=m, second=0, microsecond=0)
              for h, m in SLOTS[event_cron]]
    # A late scheduled GitHub worker still belongs to its scheduled release
    # window. No manual workflow can pass the actual-event check in process().
    if not any(0 <= (local - start).total_seconds() <= 90*60 for start in starts):
        raise ValueError("Outside scheduled editorial window")
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
    if not dry_run and (os.getenv("GITHUB_EVENT_NAME") != "schedule" or
                        os.getenv("GITHUB_ACTIONS") != "true" or
                        not os.getenv("GH_TOKEN") or
                        not re.fullmatch(r"[\w.-]+/[\w.-]+", repo)):
        raise RuntimeError("Automatic PR merges require a real scheduled GitHub Master event")
    print(f"EDITORIAL QUEUE: {len(items)} approved PR(s) due in this window", flush=True)
    for entry in items:
        pr, pin = entry["pr"], entry["head_sha"]
        if dry_run:
            print(f"EDITORIAL QUEUE DRY-RUN: #{pr}, SHA {pin[:12]}")
            continue
        try:
            info = json.loads(cli("gh", "pr", "view", str(pr), "--repo", repo,
                                  "--json", "state,headRefOid,baseRefName,isDraft"))
            if info["state"] == "MERGED":
                print(f"EDITORIAL QUEUE: #{pr} already merged")
                continue
            if (info["state"] != "OPEN" or info["isDraft"] or
                    info["baseRefName"] != "main" or info["headRefOid"] != pin):
                print(f"::warning::EDITORIAL QUEUE: #{pr} differs from "
                      "the editor-approved revision; retain for reapproval", flush=True)
                continue
            cli("gh", "pr", "merge", str(pr), "--repo", repo, "--squash",
                "--match-head-commit", pin)
            print(f"EDITORIAL QUEUE: merged #{pr} at its approved slot", flush=True)
        except (subprocess.SubprocessError, OSError, ValueError, KeyError) as exc:
            # No single PR is allowed to block unrelated approved PRs or imports.
            print(f"::warning::EDITORIAL QUEUE: #{pr} still pending: "
                  f"{str(exc)[:320]}", flush=True)


def self_test() -> None:
    t = datetime.fromisoformat("2026-10-21T12:46:00+02:00")
    data = {"version": 1, "items": [
        {"pr": 119, "head_sha": "a"*40,
         "publish_at": "2026-10-21T12:45:00+02:00", "owner_approved": True},
        {"pr": 118, "head_sha": "b"*40,
         "publish_at": "2026-10-22T10:15:00+02:00", "owner_approved": True},
    ]}
    assert [x["pr"] for x in due_items(data, t, "45 12,17 * * *")] == [119]
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
