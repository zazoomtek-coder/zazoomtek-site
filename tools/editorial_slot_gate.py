#!/usr/bin/env python3
"""Strict Europe/Rome editorial gate.

The workflow imports sources first. This gate then compares the resulting
published-content snapshots with the last successful release. No content
change means no build and no deployment.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
import hashlib
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "data" / "editorial_release_state.json"
ROME = ZoneInfo("Europe/Rome")
SLOTS = ((12, 30), (16, 0), (19, 30))
# Only editorial payloads are fingerprinted. Code, templates, workflow files,
# verification scripts and unused uploaded files cannot trigger a release.
CONTENT_FILES = (
    "data/community_imported.json",
    "data/videos.json",
    "data/web.json",
    "data/studio_posts.json",
    "data/studio_overrides.json",
)


def content_digest():
    hasher = hashlib.sha256()
    for filename in CONTENT_FILES:
        path = ROOT / filename
        if not path.is_file():
            raise RuntimeError("Missing editorial content snapshot: " + filename)
        hasher.update(filename.encode("utf-8") + b"\0")
        hasher.update(path.read_bytes() + b"\0")
    # Include only media referenced by approved Studio publications.
    referenced = set()
    for filename, key in (("studio_posts.json", "posts"),
                          ("studio_overrides.json", "overrides")):
        payload = json.loads((ROOT / "data" / filename).read_text(encoding="utf-8"))
        rows = payload.get(key, [])
        records = rows if isinstance(rows, list) else rows.values()
        for row in records:
            if not isinstance(row, dict):
                continue
            urls = [row.get("image")]
            urls.extend(block.get("url") for block in row.get("body", [])
                        if isinstance(block, dict))
            for url in urls:
                if isinstance(url, str) and url.startswith("/assets/uploads/"):
                    relative = url.lstrip("/")
                    if relative.startswith("assets/uploads/") and ".." not in Path(relative).parts:
                        referenced.add(relative)
    for relative in sorted(referenced):
        path = ROOT / relative
        if not path.is_file():
            raise RuntimeError("Approved editorial media is missing: " + relative)
        hasher.update(relative.encode("utf-8") + b"\0")
        hasher.update(path.read_bytes() + b"\0")
    return hasher.hexdigest()


def state():
    try:
        value = json.loads(STATE.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def requested_slot(now):
    """Validate the exact slot supplied by the Worker, including DST date."""
    value = os.getenv("EDITORIAL_REQUESTED_SLOT", "")
    if value not in ("12:30", "16:00", "19:30"):
        return None
    hour, minute = map(int, value.split(":"))
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if now < target or now >= target + timedelta(minutes=30):
        return None
    return target


def emit(name, value):
    path = os.getenv("GITHUB_ENV")
    if not path:
        raise RuntimeError("GITHUB_ENV absent; refuses any deployment")
    with open(path, "a", encoding="utf-8") as output:
        output.write(f"{name}={value}\n")


def prepare():
    now = datetime.now(ROME)
    slot = requested_slot(now)
    if slot is None:
        print("SKIPPED: not one of the three exact release slots", now.isoformat(), flush=True)
        emit("EDITORIAL_NEEDS_RELEASE", "false")
        return

    current_digest = content_digest()
    previous = state()
    if previous.get("slot") == slot.isoformat():
        print("SKIPPED: this daily slot has already been released", slot.isoformat(), flush=True)
        emit("EDITORIAL_NEEDS_RELEASE", "false")
        return
    if previous.get("content_digest") == current_digest:
        print("SKIPPED: import completed but no new or changed editorial content exists",
              current_digest[:20], flush=True)
        emit("EDITORIAL_NEEDS_RELEASE", "false")
        return

    print("NEW EDITORIAL CONTENT VERIFIED; release candidate",
          slot.isoformat(), "digest", current_digest[:20], flush=True)
    emit("EDITORIAL_NEEDS_RELEASE", "true")
    emit("EDITORIAL_TARGET", slot.isoformat())
    emit("EDITORIAL_CONTENT_DIGEST", current_digest)


def authorize():
    slot_value = os.getenv("EDITORIAL_TARGET")
    expected_digest = os.getenv("EDITORIAL_CONTENT_DIGEST")
    if not slot_value or not expected_digest:
        raise RuntimeError("Missing slot or verified content digest")
    slot = datetime.fromisoformat(slot_value)
    now = datetime.now(ROME)
    if slot.tzinfo is None or now < slot or now >= slot + timedelta(minutes=30):
        emit("EDITORIAL_RELEASE_AUTHORIZED", "false")
        print("SKIPPED: exact slot window has expired", now.isoformat(), flush=True)
        return
    previous = state()
    if previous.get("slot") == slot.isoformat():
        emit("EDITORIAL_RELEASE_AUTHORIZED", "false")
        print("SKIPPED: slot already released by another run", slot.isoformat(), flush=True)
        return
    # Recheck after the import/build preparation to ensure content is still
    # exactly the verified snapshot and has not disappeared or been replaced.
    if content_digest() != expected_digest:
        emit("EDITORIAL_RELEASE_AUTHORIZED", "false")
        print("SKIPPED: editorial content changed after preflight; require next slot", flush=True)
        return
    emit("EDITORIAL_RELEASE_AUTHORIZED", "true")
    print("AUTHORIZED: verified new content in exact slot", slot.isoformat(), flush=True)


def stamp():
    slot_value = os.getenv("EDITORIAL_TARGET")
    expected_digest = os.getenv("EDITORIAL_CONTENT_DIGEST")
    if (not slot_value or not expected_digest
            or os.getenv("EDITORIAL_RELEASE_AUTHORIZED") != "true"):
        raise RuntimeError("Cannot record an unauthorized editorial release")
    actual_digest = content_digest()
    if actual_digest != expected_digest:
        raise RuntimeError("Content digest changed before release receipt")
    body = {
        "slot": slot_value,
        "content_digest": actual_digest,
        "finished_at": datetime.now(ROME).isoformat(timespec="seconds"),
    }
    STATE.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8")
    print("SUCCESSFUL EDITORIAL RELEASE RECEIPT", body, flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("prepare", "authorize", "stamp"):
        raise SystemExit("usage: editorial_slot_gate.py prepare|authorize|stamp")
    globals()[sys.argv[1]]()
