#!/usr/bin/env python3
"""Read-only inventory of competing ZazoomTek GitHub Actions writers.

A report is NOT a workflow-disable operation. Until a reviewed atomic
cutover installs the sole master production writer, never disable legacy jobs.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PROTECTED_WRITERS = {
    "youtube-sync.yml",
    "refresh-static-news-in-evidenza.yml",
    "refresh-home-editorials-daily.yml",
    "cloudflare-controlled-release.yml",
    "publish-approved-reviews.yml",
    "publish-standard-news.yml",
    "publish-special-news.yml",
}
WRITE_LINE = re.compile(
    r"\b(?:git\s+push|git\s+commit|gh\s+api\s+.+(?:POST|PUT|PATCH)|"
    r"wrangler\s+pages\s+deploy|firebase\s+deploy)\b", re.I)


def summarize(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    first = next((x for x in lines if x.startswith("name:")), path.name)
    schedule = bool(re.search(r"(?m)^\s{2}schedule\s*:", raw))
    dispatch = bool(re.search(r"(?m)^\s{2}workflow_dispatch\s*:", raw))
    writer = bool(re.search(r"(?m)^\s*contents:\s*write\b", raw)) or bool(WRITE_LINE.search(raw))
    # 'schedule' is in the workflow trigger, not a textual comment.
    return {"file": path.name, "name": first.removeprefix("name:").strip(),
            "schedule": schedule, "manual_trigger": dispatch,
            "potential_writer": writer}


def report(root: Path) -> dict:
    folder = root / ".github/workflows"
    workflows = [summarize(x) for x in sorted(folder.glob("*.yml"))]
    scheduled_writers = [x["file"] for x in workflows
                         if x["schedule"] and x["potential_writer"]]
    all_writers = [x["file"] for x in workflows if x["potential_writer"]]
    expected = sorted(PROTECTED_WRITERS & set(all_writers))
    # Only after all old scheduled writers are atomically retired and the new
    # production workflow exists can an operator APPROVE the release cutover.
    master_exists = (folder / "master-orchestrator-production.yml").exists()
    blockers = ([f"Scheduled legacy writer: {x}" for x in scheduled_writers] +
                [f"Legacy workflow with write permission: {x}" for x in all_writers
                 if x not in scheduled_writers and x != "master-orchestrator-production.yml"])
    if not master_exists:
        blockers.append("No production release workflow with single-writer lock installed")
    return {"generated_utc": datetime.now(timezone.utc).isoformat(),
            "legacy_writer_count": len(all_writers),
            "active_scheduled_writers": sorted(scheduled_writers),
            "known_critical_writers": expected,
            "production_master_exists": master_exists,
            "cutover_ready": not blockers,
            "blockers": blockers,
            "action": "Report only; NEVER disable a production job from a staging run."}


def self_test() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp) / ".github/workflows"
        folder.mkdir(parents=True)
        (folder / "old.yml").write_text(
            "name: Legacy\non:\n  schedule:\n    - cron: '0 * * * *'\n"
            "permissions:\n  contents: write\njobs:\n  publish:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - run: git push origin main\n",
            encoding="utf-8")
        data = report(Path(tmp))
        assert not data["cutover_ready"]
        assert "old.yml" in data["active_scheduled_writers"]
    print("PASS: scheduled legacy writer causes blocking audit")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--output", default="artifacts/master-orchestrator/cutover-audit.json")
    args = ap.parse_args()
    if args.self_test:
        self_test()
    else:
        data = report(ROOT)
        dest = Path(args.output)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"CUTOVER AUDIT: {data['legacy_writer_count']} potential writers; "
              f"{len(data['active_scheduled_writers'])} scheduled; "
              f"ready={data['cutover_ready']}")


if __name__ == "__main__":
    main()
