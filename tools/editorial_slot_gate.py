#!/usr/bin/env python3
"""Strict Europe/Rome editorial gate.

The workflow imports sources first. This gate then compares the resulting
published-content snapshots with the last successful release. No content
change means no build and no deployment.
"""
from datetime import datetime
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
# Only approved editorial collections and their referenced media are fingerprinted.
MAX_DISPATCH_DELAY_SECONDS = 600


# Each snapshot contributes only its actual editorial collection. Service-level
# fields (for example web.json's daily "updated" marker) are deliberately ignored.
EDITORIAL_COLLECTIONS = {
    "data/community_imported.json": "posts",
    "data/videos.json": "videos",
    "data/web.json": "items",
    "data/studio_posts.json": "posts",
    "data/studio_overrides.json": "overrides",
}
SERVICE_METADATA_KEYS = {
    "updated", "updated_at", "created_at", "generated_at", "synced_at",
    "fetched_at", "last_updated", "last_synced", "first_seen_at",
    "source_updated_at", "cache_updated_at",
}


def editorial_value(value):
    """Return stable editorial data, excluding generated/service metadata."""
    if isinstance(value, dict):
        return {
            key: editorial_value(item)
            for key, item in sorted(value.items())
            if key not in SERVICE_METADATA_KEYS
        }
    if isinstance(value, list):
        return [editorial_value(item) for item in value]
    return value


def content_digest():
    hasher = hashlib.sha256()
    for filename, collection in EDITORIAL_COLLECTIONS.items():
        path = ROOT / filename
        if not path.is_file():
            raise RuntimeError("Missing editorial content snapshot: " + filename)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeError, ValueError) as exc:
            raise RuntimeError("Invalid editorial content snapshot: " + filename) from exc
        if not isinstance(payload, dict) or collection not in payload:
            raise RuntimeError("Missing editorial collection " + collection + " in " + filename)
        records = payload[collection]
        if collection == "overrides":
            if not isinstance(records, dict):
                raise RuntimeError("Invalid editorial collection overrides in " + filename)
        elif not isinstance(records, list):
            raise RuntimeError("Invalid editorial collection " + collection + " in " + filename)
        canonical = json.dumps(
            editorial_value(records), ensure_ascii=False, sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        hasher.update(filename.encode("utf-8") + b"\0")
        hasher.update(canonical + b"\0")

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
    """Resolve the validated Rome slot, or an explicit immediate release."""
    if os.getenv("EDITORIAL_FORCE_RELEASE", "").lower() == "true":
        return now.replace(second=0, microsecond=0)

    value = os.getenv("EDITORIAL_REQUESTED_SLOT", "")
    if value not in ("12:30", "16:00", "19:30"):
        return None
    hour, minute = map(int, value.split(":"))
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # The workflow's first job validates the actual dispatch against this
    # slot with a ±10-minute tolerance. Preserve that decision while the
    # importer runs, even if importing takes longer than the dispatch window.
    if os.getenv("EDITORIAL_SLOT_GATE_PASSED", "").lower() == "true":
        return target

    delay_seconds = abs((now - target).total_seconds())
    if delay_seconds > MAX_DISPATCH_DELAY_SECONDS:
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
    force_release = os.getenv("EDITORIAL_FORCE_RELEASE", "").lower() == "true"
    slot = requested_slot(now)
    if slot is None:
        print("SKIPPED: not one of the three authorized release slots", now.isoformat(), flush=True)
        emit("EDITORIAL_NEEDS_RELEASE", "false")
        return

    current_digest = content_digest()
    previous = state()
    if not force_release and previous.get("slot") == slot.isoformat():
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
    force_release = os.getenv("EDITORIAL_FORCE_RELEASE", "").lower() == "true"
    slot_gate_passed = os.getenv("EDITORIAL_SLOT_GATE_PASSED", "").lower() == "true"
    # The workflow gate already validated the dispatch within ±10 minutes.
    # Do not reapply a second clock check after the potentially long import/build.
    if not force_release and not slot_gate_passed:
        delay_seconds = (now - slot).total_seconds()
        if (slot.tzinfo is None or now.date() != slot.date()
                or abs(delay_seconds) > MAX_DISPATCH_DELAY_SECONDS):
            emit("EDITORIAL_RELEASE_AUTHORIZED", "false")
            print("SKIPPED: release slot is invalid or outside ±10 minutes",
                  now.isoformat(), flush=True)
            return
    previous = state()
    if not force_release and previous.get("slot") == slot.isoformat():
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
