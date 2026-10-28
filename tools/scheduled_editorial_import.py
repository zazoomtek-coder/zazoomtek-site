#!/usr/bin/env python3
"""ZazoomTek editorial import. Run before approved 12:30/19:30 releases.

Safely combine full original YouTube Community posts, channel RSS videos,
previously staged queue records and six external RSS sources.
Failures retain the last valid content; this script NEVER deploys.
"""
import json
import re
import subprocess
from pathlib import Path

from emergency_sync import youtube_videos, youtube_community, refresh_rss

DATA = Path(__file__).resolve().parents[1] / "data"


def snapshot(name, key):
    value = json.loads((DATA / name).read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get(key), list):
        raise ValueError("Invalid editorial snapshot: " + name)
    return value


def read_queue(name, key):
    try:
        output = subprocess.check_output(
            ["git", "show", "origin/editorial-queue:data/" + name],
            stderr=subprocess.DEVNULL, timeout=15,
        )
        obj = json.loads(output.decode("utf-8"))
        return obj.get(key, []) if isinstance(obj.get(key), list) else []
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
            UnicodeError, ValueError) as e:
        print("QUEUE BACKUP UNAVAILABLE", name, type(e).__name__, flush=True)
        return []


def merge_queue(queue_file, dest_file, key, archived):
    source = read_queue(queue_file, key)
    doc = snapshot(dest_file, key)
    rows = doc[key]
    ids = {r.get("id") for r in rows if isinstance(r, dict)}
    added = []
    for r in source:
        if not isinstance(r, dict):
            continue
        rid = r.get("id")
        if not rid or rid in ids or rid in archived:
            continue
        if key == "posts":
            if not (re.fullmatch(r"Ug[A-Za-z0-9_-]{12,}", str(rid)) and
                    r.get("text_complete") and r.get("type") and
                    len(r.get("text") or "") >= 60):
                continue
        else:
            if not re.fullmatch(r"[A-Za-z0-9_-]{11}", str(rid)):
                continue
        clean = {k: v for k, v in r.items() if k != "first_seen_at"}
        rows.append(clean)
        ids.add(rid)
        added.append(clean)
    if added:
        doc[key] = sorted(
            rows, key=lambda x: str(x.get("published_at") or x.get("date") or ""),
            reverse=True,
        )
        (DATA / dest_file).write_text(
            json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
        )
    print("QUEUE RESTORED", queue_file, len(added), flush=True)
    return added


def main():
    before = {name: len(snapshot(name, key)[key]) for name, key in
              (("community_imported.json", "posts"), ("videos.json", "videos"))}
    archive = {x.get("id") for x in snapshot("community_full.json", "posts")["posts"]}
    queue_posts = merge_queue("queue_community.json", "community_imported.json",
                              "posts", archive)
    queue_videos = merge_queue("queue_videos.json", "videos.json", "videos", set())
    # Network errors are handled within these source functions. A blocked
    # YouTube or RSS endpoint cannot delete the published editorial archive.
    results = {}
    for name, task in (("videos", youtube_videos),
                       ("community", youtube_community),
                       ("rss", refresh_rss)):
        try:
            results[name] = bool(task())
        except Exception as exc:
            results[name] = False
            print("LIVE SOURCE FAILED; archived content preserved:",
                  name, type(exc).__name__, str(exc)[:170], flush=True)
    after = {name: len(snapshot(name, key)[key]) for name, key in
             (("community_imported.json", "posts"), ("videos.json", "videos"))}
    print("IMPORT RESULT",
          "new Community:", after["community_imported.json"] - before["community_imported.json"],
          "new videos:", after["videos.json"] - before["videos.json"],
          "RSS OK:", results["rss"], flush=True)
    print("LIVE SOURCES:", results, flush=True)
    for p in snapshot("community_imported.json", "posts")["posts"][:8]:
        print("LATEST COMMUNITY", p.get("date"), str(p.get("title", ""))[:130], flush=True)
    # An unavailable source never causes a fictitious success claim; the
    # release decision is separately driven by real changed content files.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
