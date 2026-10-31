#!/usr/bin/env python3
"""Exactly three authorized editorial release slots in Europe/Rome, idempotently.

- prepare: decide if the imported data changed since the last successful deploy
- authorize: sleep until 12:30, 16:00 or 19:30, reject out-of-slot publishing
- stamp: record a successful Cloudflare deployment for deduplication
Only Cloudflare Wrangler itself deploys; this module never accesses Cloudflare.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
import hashlib
import json
import os
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "data" / "editorial_release_state.json"
FILES = (
    "data/community_imported.json",
    "data/videos.json",
    "data/web.json",
    "data/studio_posts.json",
    "data/studio_overrides.json",
    # Approved Studio editor features are delivered at the next editorial slot,
    # even if no new news happens to arrive. Otherwise a changed editor could
    # remain unpublished indefinitely while all editorial JSON is unchanged.
    "tools/studio_v2_build.py",
    "assets/js/studio-v2.js",
    "assets/css/studio-v2.css",
    "tools/community_youtube.py",
    "tools/build.py",
    "tools/seo.py",
    "tools/verify_seo.py",
    "tools/scheduled_editorial_import.py",
    # Aggiornamenti server Studio al prossimo slot.
    "functions/api/studio/[[path]].js",
    # Anche le correzioni grafiche approvate richiedono lo slot.
    "assets/css/spotnews.css",
)
ROME = ZoneInfo("Europe/Rome")


def digest():
    hasher = hashlib.sha256()
    for filename in FILES:
        data = (ROOT / filename).read_bytes()
        hasher.update(filename.encode("utf-8") + b"\x00" + data + b"\x00")
    # Uploaded media is a published dependency of Studio articles: the
    # content fingerprint must change when previously missing assets arrive.
    uploads = ROOT / "assets" / "uploads"
    if uploads.exists():
        for file in sorted(p for p in uploads.rglob("*") if p.is_file()):
            name = file.relative_to(ROOT).as_posix()
            hasher.update(name.encode("utf-8") + b"\x00")
            hasher.update(file.read_bytes() + b"\x00")
    return hasher.hexdigest()


def state():
    try:
        ob = json.loads(STATE.read_text(encoding="utf-8"))
        return ob if isinstance(ob, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def event_slot(now):
    for hour, minute in ((12, 30), (16, 0), (19, 30)):
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target - timedelta(minutes=15) <= now < target + timedelta(hours=1):
            return target
    return None


def emit(name, value):
    path = os.getenv("GITHUB_ENV")
    if not path:
        raise RuntimeError("GITHUB_ENV absent; refuses any deployment")
    with open(path, "a", encoding="utf-8") as out:
        out.write(f"{name}={value}\n")


def prepare():
    now = datetime.now(ROME)
    slot = event_slot(now)
    if slot is None:
        print("NOT AN EDITORIAL SLOT:", now.isoformat(), flush=True)
        emit("EDITORIAL_NEEDS_RELEASE", "false")
        return
    old = state()
    current = digest()
    if old.get("slot") == slot.isoformat():
        print("THIS SLOT IS ALREADY PUBLISHED", slot.isoformat(), flush=True)
        emit("EDITORIAL_NEEDS_RELEASE", "false")
        return
    if old.get("content_digest") == current:
        print("NO NEW YOUTUBE/RSS CONTENT. No deployment this slot.", flush=True)
        emit("EDITORIAL_NEEDS_RELEASE", "false")
        return
    print("NEW VERIFIED EDITORIAL CONTENT:", slot.isoformat(),
          "SHA256:", current[:20], flush=True)
    emit("EDITORIAL_NEEDS_RELEASE", "true")
    emit("EDITORIAL_TARGET", slot.isoformat())


def authorize():
    slot_str = os.getenv("EDITORIAL_TARGET")
    if not slot_str:
        raise RuntimeError("Missing authorized slot")
    slot = datetime.fromisoformat(slot_str)
    if slot.tzinfo is None:
        raise RuntimeError("Unaware editorial slot")
    now = datetime.now(ROME)
    if now < slot:
        seconds = (slot - now).total_seconds()
        print("PREPARED; waiting until the ONLY authorized release slot",
              slot.isoformat(), "seconds", round(seconds), flush=True)
        time.sleep(seconds + 0.3)
    now = datetime.now(ROME)
    if not (slot <= now < slot + timedelta(hours=1)):
        print("SKIPPED: slot expired; no out-of-window deployment",
              now.isoformat(), flush=True)
        emit("EDITORIAL_RELEASE_AUTHORIZED", "false")
        return
    # Another run for the same slot may have completed while this one was queued.
    if state().get("slot") == slot.isoformat():
        print("SKIPPED: slot already released by an earlier run", flush=True)
        emit("EDITORIAL_RELEASE_AUTHORIZED", "false")
        return
    print("AUTHORIZED EXACT SLOT", slot.isoformat(), "started", now.isoformat(), flush=True)
    emit("EDITORIAL_RELEASE_AUTHORIZED", "true")


def stamp():
    slot = os.getenv("EDITORIAL_TARGET")
    if not slot or os.getenv("EDITORIAL_RELEASE_AUTHORIZED") != "true":
        raise RuntimeError("Cannot mark an unauthorized release")
    body = {
        "slot": slot,
        "content_digest": digest(),
        "finished_at": datetime.now(ROME).isoformat(timespec="seconds"),
    }
    STATE.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("SUCCESSFUL DEPLOY RECEIPT", body, flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("prepare", "authorize", "stamp"):
        raise SystemExit("usage: editorial_slot_gate.py prepare|authorize|stamp")
    globals()[sys.argv[1]]()
