#!/usr/bin/env python3
"""Remove only today's YouTube queue entries already imported and verified live.

This job never edits main, published archives, Studio, or site files. It writes
only data/queue_community.json and data/queue_videos.json on editorial-queue.
"""
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import html
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

ROME = ZoneInfo("Europe/Rome")
BASE = "https://zazoomtek.it"
REPO = os.environ.get("GITHUB_REPOSITORY", "zazoomtek-coder/zazoomtek-site")


def read_json(path, key):
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict) or not isinstance(obj.get(key), list):
        raise ValueError("Invalid queue/publication snapshot: " + str(path))
    return obj


def local_day(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=ROME)
        return stamp.astimezone(ROME).date()
    except (ValueError, TypeError, OverflowError):
        return None


def fetch(url, timeout=18):
    request = urllib.request.Request(url, headers={
        "User-Agent": "ZazoomTek-Daily-Queue-Cleanup/1.0",
        "Cache-Control": "no-cache",
    })
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError("HTTP " + str(response.status) + ": " + url)
        return response.read().decode("utf-8", errors="replace")


def publisher_is_active():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN unavailable; cleanup is not allowed")
    url = ("https://api.github.com/repos/" + REPO +
           "/actions/workflows/editorial-publish.yml/runs?branch=main&per_page=50")
    request = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ZazoomTek-Daily-Queue-Cleanup/1.0",
    })
    with urllib.request.urlopen(request, timeout=18) as response:
        payload = json.loads(response.read().decode("utf-8"))
    active = [run for run in payload.get("workflow_runs", [])
              if run.get("status") in ("queued", "in_progress", "waiting", "requested")]
    if active:
        print("CLEANUP DEFERRED: editorial publisher still active:",
              [(x.get("id"), x.get("status")) for x in active[:5]], flush=True)
        return True
    return False


def verified_community(row, sitemap_paths):
    pid = str(row.get("id") or "")
    if not re.fullmatch(r"Ug[A-Za-z0-9_-]{12,}", pid):
        return False
    slug = "community-" + re.sub(r"[^a-z0-9]+", "-", pid.lower()).strip("-")
    if slug not in sitemap_paths:
        print("KEEP Community: missing from live sitemap:", pid, flush=True)
        return False
    title = str(row.get("title") or "").strip()
    if not title:
        return False
    display_title = re.sub(
        r"^\s*(?:News|Review|Recensione)(?:\s+(?:Tech|Gaming|Extra))?\s*[:\u2013\u2014-]\s*",
        "", title, flags=re.I)
    try:
        page = html.unescape(fetch(BASE + "/" + slug))
    except (OSError, urllib.error.URLError, ValueError, RuntimeError) as exc:
        print("KEEP Community: live page unavailable:", pid, str(exc)[:140], flush=True)
        return False
    if len(display_title) < 20 or display_title[:45] not in page:
        print("KEEP Community: live title not verified:", pid, flush=True)
        return False
    return True


def verified_video(row, live_video_pages):
    vid = str(row.get("id") or "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid):
        return False
    title = str(row.get("title") or "").strip()
    if not title:
        return False
    needle = "watch?v=" + vid
    for page in live_video_pages:
        if needle in page and title in page:
            return True
    print("KEEP video: ID/title not individually visible on live site:", vid, flush=True)
    return False


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: queue_daily_cleanup.py MAIN_CHECKOUT QUEUE_CHECKOUT")
    main_root = Path(sys.argv[1]).resolve()
    queue_root = Path(sys.argv[2]).resolve()
    now = datetime.now(ROME)
    clock = now.time()
    if not (clock > time(19, 45) or clock < time(3, 0)):
        print("CLEANUP WINDOW CLOSED:", now.isoformat(), flush=True)
        return 0
    target_day = now.date() if clock > time(19, 45) else now.date() - timedelta(days=1)
    print("DAILY QUEUE CLEANUP CHECK:", target_day.isoformat(), now.isoformat(), flush=True)

    # A successful release receipt for the target day is mandatory. The last
    # successful slot may be 12:30, 16:00 or 19:30 if later slots had no changes.
    state = json.loads((main_root / "data/editorial_release_state.json").read_text(encoding="utf-8"))
    slot = datetime.fromisoformat(str(state.get("slot") or ""))
    finished = datetime.fromisoformat(str(state.get("finished_at") or ""))
    if slot.astimezone(ROME).date() != target_day or slot.astimezone(ROME).time().replace(tzinfo=None) not in (
        time(12, 30), time(16, 0), time(19, 30)
    ) or finished.astimezone(ROME).date() != target_day:
        print("CLEANUP DEFERRED: no successful editorial release receipt for", target_day, flush=True)
        return 0

    if publisher_is_active():
        return 0

    community_path = queue_root / "data/queue_community.json"
    videos_path = queue_root / "data/queue_videos.json"
    community_text = community_path.read_text(encoding="utf-8")
    videos_text = videos_path.read_text(encoding="utf-8")
    community_doc = read_json(community_path, "posts")
    videos_doc = read_json(videos_path, "videos")
    imported_community = read_json(main_root / "data/community_imported.json", "posts")
    imported_videos = read_json(main_root / "data/videos.json", "videos")
    community_ids = {str(x.get("id")) for x in imported_community["posts"] if isinstance(x, dict)}
    video_ids = {str(x.get("id")) for x in imported_videos["videos"] if isinstance(x, dict)}

    sitemap_xml = fetch(BASE + "/sitemap.xml")
    sitemap_paths = set()
    for node in ET.fromstring(sitemap_xml).iter():
        if node.tag.rsplit("}", 1)[-1] == "loc" and node.text:
            path = node.text.rstrip("/").split("/")[-1]
            sitemap_paths.add(path)

    # / and /video are the only live site modules rendering individual upload
    # cards; each currently exposes at most the latest four videos. Older IDs
    # therefore remain in the queue unless their own card is actually public.
    live_video_pages = []
    for url in (BASE + "/", BASE + "/video"):
        try:
            live_video_pages.append(html.unescape(fetch(url)))
        except (OSError, urllib.error.URLError, ValueError, RuntimeError) as exc:
            print("LIVE video listing unavailable:", url, str(exc)[:120], flush=True)

    remove_community = set()
    for row in community_doc["posts"]:
        if not isinstance(row, dict) or local_day(row.get("first_seen_at")) != target_day:
            continue
        pid = str(row.get("id") or "")
        if pid in community_ids and verified_community(row, sitemap_paths):
            remove_community.add(pid)

    remove_videos = set()
    for row in videos_doc["videos"]:
        if not isinstance(row, dict) or local_day(row.get("first_seen_at")) != target_day:
            continue
        vid = str(row.get("id") or "")
        if vid in video_ids and verified_video(row, live_video_pages):
            remove_videos.add(vid)

    if not remove_community and not remove_videos:
        print("CLEANUP: no same-day queue entries proven imported and live; nothing removed", flush=True)
        return 0

    # Re-read before writing; an unexpected concurrent queue change is a hard stop.
    if community_path.read_text(encoding="utf-8") != community_text or videos_path.read_text(encoding="utf-8") != videos_text:
        raise RuntimeError("Queue changed during verification; refusing to clean")

    community_doc["posts"] = [x for x in community_doc["posts"]
                              if not (isinstance(x, dict) and str(x.get("id") or "") in remove_community)]
    videos_doc["videos"] = [x for x in videos_doc["videos"]
                            if not (isinstance(x, dict) and str(x.get("id") or "") in remove_videos)]
    community_path.write_text(json.dumps(community_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    videos_path.write_text(json.dumps(videos_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Check once more immediately before the only write to editorial-queue.
    if publisher_is_active():
        community_path.write_text(community_text, encoding="utf-8")
        videos_path.write_text(videos_text, encoding="utf-8")
        print("CLEANUP ABORTED: publisher started during verification; queue restored", flush=True)
        return 0

    status = subprocess.check_output(
        ["git", "-C", str(queue_root), "status", "--porcelain"], text=True
    ).strip().splitlines()
    allowed = {"data/queue_community.json", "data/queue_videos.json"}
    changed = {line[3:] for line in status if len(line) >= 4}
    if not changed.issubset(allowed):
        raise RuntimeError("Unexpected queue checkout changes; refusing commit: " + repr(changed))
    if not changed:
        print("CLEANUP: queue already clean", flush=True)
        return 0

    subprocess.run(["git", "-C", str(queue_root), "config", "user.name", "ZazoomTek Queue Cleanup"], check=True)
    subprocess.run(["git", "-C", str(queue_root), "config", "user.email",
                    "41898282+github-actions[bot]@users.noreply.github.com"], check=True)
    subprocess.run(["git", "-C", str(queue_root), "add",
                    "data/queue_community.json", "data/queue_videos.json"], check=True)
    subprocess.run(["git", "-C", str(queue_root), "commit", "-m",
                    "Rimuovi dalla coda solo contenuti di oggi verificati live"], check=True)
    subprocess.run(["git", "-C", str(queue_root), "push", "origin", "HEAD:editorial-queue"], check=True)
    print("CLEANUP COMPLETE:",
          len(remove_community), "Community and", len(remove_videos),
          "videos removed from editorial-queue only.", flush=True)
    print("Published archives, Studio, main and the live site were not modified.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
