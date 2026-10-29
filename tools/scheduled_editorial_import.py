#!/usr/bin/env python3
"""ZazoomTek editorial import. Run before approved 12:30/19:30 releases.

Safely combine full original YouTube Community posts, channel RSS videos,
previously staged queue records and six external RSS sources.
Failures retain the last valid content; this script NEVER deploys.
"""
import json
import re
import subprocess
from datetime import datetime
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




# Studio writes approved publications to the protected editorial-queue branch.
# These TWO data files and newly uploaded assets must be copied to the release
# snapshot, otherwise "Pubblica" is acknowledged but NEVER goes live.
# Drafts (data/studio_v2_drafts.json) are NEVER imported or published.
STUDIO_CATEGORIES = {
    "news-tech", "news-gaming", "recensioni-tech", "recensioni-gaming",
    "guide", "speciali", "extra",
}
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _date_stamp(row):
    try:
        date = str(row.get("updated_at") or row.get("published_at") or "")
        if date:
            return datetime.fromisoformat(date.replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError, OverflowError):
        pass
    return 0


def _valid_studio_row(row, slug=None):
    if not isinstance(row, dict) or row.get("source") != "studio-editor":
        return False
    key = row.get("slug")
    if not isinstance(key, str) or not SLUG.fullmatch(key) or len(key) > 150:
        return False
    if slug is not None and key != slug:
        return False
    if row.get("category") not in STUDIO_CATEGORIES or not row.get("image"):
        return False
    if not isinstance(row.get("title"), str) or len(row["title"]) < 12:
        return False
    body = row.get("body")
    if not isinstance(body, list) or not (1 <= len(body) <= 160):
        return False
    words = " ".join(str(b.get("text", "")) for b in body
                     if isinstance(b, dict) and b.get("type") in ("paragraph", "quote"))
    return len(words.strip()) >= 260


def sync_studio_publications():
    """Merge ONLY explicitly published Studio data, never its saved drafts.

    Per-slug upsert retains unrelated main records, and prevents an older queue
    revision from overwriting a newer entry already present on main.
    """
    added = 0
    for filename, key in (("studio_posts.json", "posts"),
                          ("studio_overrides.json", "overrides")):
        queued = read_queue(filename, key)
        path = DATA / filename
        old = snapshot(filename, key)
        rows = old[key]
        changed = False
        if key == "posts":
            indexed = {r.get("slug"): i for i, r in enumerate(rows)
                       if isinstance(r, dict) and isinstance(r.get("slug"), str)}
            for item in queued:
                if not _valid_studio_row(item):
                    continue
                idx = indexed.get(item["slug"])
                if idx is None:
                    rows.insert(0, item)
                    indexed = {r["slug"]: i for i, r in enumerate(rows)
                               if isinstance(r, dict) and r.get("slug")}
                    changed = True
                    added += 1
                elif rows[idx] != item and _date_stamp(item) > _date_stamp(rows[idx]):
                    rows[idx] = item
                    changed = True
                    added += 1
        else:
            # A queue override is a mapping keyed by canonical article slug.
            try:
                raw = subprocess.check_output(
                    ["git", "show", "origin/editorial-queue:data/" + filename],
                    stderr=subprocess.DEVNULL, timeout=15,
                )
                queue_obj = json.loads(raw.decode("utf-8")).get(key, {})
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
                    UnicodeError, ValueError):
                queue_obj = {}
            if isinstance(queue_obj, dict):
                for slug, item in queue_obj.items():
                    if not _valid_studio_row(item, slug):
                        continue
                    current = rows.get(slug)
                    if current is None or (current != item and _date_stamp(item) > _date_stamp(current)):
                        rows[slug] = item
                        changed = True
                        added += 1
        if changed:
            path.write_text(json.dumps(old, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
        print("STUDIO PUBLISH SYNC", filename, "updated:", changed, flush=True)
    return added


def sync_studio_assets():
    """Copy only missing, approved Studio upload paths from the queue branch.

    Do not overwrite or remove existing assets; never copy a draft, editor
    source, workflow, or any path outside assets/uploads/.
    """
    root = DATA.parent
    try:
        names = subprocess.check_output(
            ["git", "ls-tree", "-r", "--name-only", "origin/editorial-queue", "--", "assets/uploads"],
            stderr=subprocess.DEVNULL, timeout=15,
        ).decode("utf-8").splitlines()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, UnicodeError):
        print("STUDIO ASSETS BACKUP unavailable; existing files retained.", flush=True)
        return 0
    added = 0
    safe = re.compile(r"^assets/uploads/[a-z0-9-]+/[a-z0-9-]+\.(?:jpg|jpeg|png|webp|mp3|m4a|wav|pdf|txt)$")
    for name in names[:1500]:
        if not safe.fullmatch(name):
            continue
        target = root / name
        if target.exists():
            continue
        try:
            blob = subprocess.check_output(
                ["git", "show", "origin/editorial-queue:" + name],
                stderr=subprocess.DEVNULL, timeout=15,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            continue
        if not (0 < len(blob) <= 12000000):
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)
        added += 1
    print("STUDIO ASSETS SYNC", added, "new media files", flush=True)
    return added

def main():
    before = {name: len(snapshot(name, key)[key]) for name, key in
              (("community_imported.json", "posts"), ("videos.json", "videos"))}
    archive = {x.get("id") for x in snapshot("community_full.json", "posts")["posts"]}
    queue_posts = merge_queue("queue_community.json", "community_imported.json",
                              "posts", archive)
    queue_videos = merge_queue("queue_videos.json", "videos.json", "videos", set())
    studio_updates = sync_studio_publications()
    studio_assets = sync_studio_assets()
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
          "RSS OK:", results["rss"],
          "Studio publications:", studio_updates, "Studio uploads:", studio_assets, flush=True)
    print("LIVE SOURCES:", results, flush=True)
    for p in snapshot("community_imported.json", "posts")["posts"][:8]:
        print("LATEST COMMUNITY", p.get("date"), str(p.get("title", ""))[:130], flush=True)
    # An unavailable source never causes a fictitious success claim; the
    # release decision is separately driven by real changed content files.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
