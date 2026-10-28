#!/usr/bin/env python3
"""One-time production recovery: import genuine ZazoomTek posts and verified RSS headlines.

Never replace existing articles with invented text; preserve previous snapshots on source errors.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from pathlib import Path
import json
import re
import urllib.request
import xml.etree.ElementTree as ET

from community_youtube import discover, date_from_relative
from sync_videos import CHANNEL_ID, NS, classify
from build import tech_sources, rss_card_for_source

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CATCHUP_FROM = "2026-10-22"

def load(name, key):
    path = DATA / name
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict) or not isinstance(obj.get(key), list):
        raise ValueError("Invalid editorial data: " + name)
    return obj

def save(name, obj):
    path = DATA / name
    updated = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    if path.read_text(encoding="utf-8") != updated:
        path.write_text(updated, encoding="utf-8")
        return True
    return False

def classify_upload(title):
    original = classify(title)
    if original:
        return original
    low = title.casefold()
    if "short" in low:
        return "short", "general"
    if "gameplay" in low:
        return "gameplay", "gaming"
    if "trailer" in low:
        return "trailer", "gaming"
    return "video", "general"

def youtube_videos():
    db = load("videos.json", "videos")
    known = {r.get("id"): r for r in db["videos"] if r.get("id")}
    url = "https://www.youtube.com/feeds/videos.xml?channel_id=" + CHANNEL_ID
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; ZazoomTek/1.0)"})
        with urllib.request.urlopen(request, timeout=25) as response:
            xml = ET.fromstring(response.read(2_000_000))
        count = 0
        recent = []
        for item in xml.findall("atom:entry", NS):
            video_id = item.findtext("yt:videoId", default="", namespaces=NS)
            title = item.findtext("atom:title", default="", namespaces=NS)
            published_at = item.findtext("atom:published", default="", namespaces=NS)
            if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id) or not title or not published_at:
                continue
            if published_at[:10] >= CATCHUP_FROM:
                recent.append((published_at[:10], title))
            if video_id in known:
                continue
            kind, topic = classify_upload(title)
            known[video_id] = {"id": video_id, "title": title, "date": published_at, "topic": topic, "kind": kind}
            count += 1
        db["videos"] = sorted(known.values(), key=lambda x: x.get("date", ""), reverse=True)
        save("videos.json", db)
        print("YOUTUBE RSS: available, added", count, "valid review/test/unboxing videos; recent uploads:", len(recent), flush=True)
        for date, title in recent[:18]:
            print("  video", date, title[:145], flush=True)
        return True
    except Exception as exc:
        print("YOUTUBE RSS UNAVAILABLE:", type(exc).__name__, str(exc)[:230], flush=True)
        return False

def youtube_community():
    db = load("community_imported.json", "posts")
    existing = {r.get("id"): r for r in db["posts"] if r.get("id")}
    archived = load("community_full.json", "posts")["posts"]
    archived_ids = {x.get("id") for x in archived}
    today = datetime.now(timezone.utc).date().isoformat()
    try:
        items = discover(limit=180, max_pages=15)
        added = []
        for row in items:
            post_id = row.get("id", "")
            if not re.fullmatch(r"Ug[A-Za-z0-9_-]{12,}", post_id) or not row.get("text_complete"):
                continue
            # YouTube's Italian and English relative labels may say 'ieri'/'yesterday'.
            if not row.get("date") and str(row.get("when", "")).lower().strip() in ("ieri", "yesterday"):
                parsed = datetime.now(timezone.utc) - timedelta(days=1)
                row["date"] = parsed.date().isoformat()
                row["published_at"] = parsed.isoformat(timespec="seconds")
            if not row.get("date") or not (CATCHUP_FROM <= row["date"] <= today):
                continue
            if post_id in archived_ids or post_id in existing:
                continue
            if len(row.get("text", "")) < 60 or not row.get("type"):
                continue
            existing[post_id] = row
            added.append(row)
        db["posts"] = sorted(existing.values(),
                             key=lambda p: p.get("published_at") or p.get("date") or "",
                             reverse=True)
        save("community_imported.json", db)
        print("YOUTUBE COMMUNITY: verified recent records", len(items),
              "new full posts", len(added), "total imported", len(db["posts"]), flush=True)
        for row in added[:35]:
            print("  community", row.get("date"), row.get("title", "")[:145], flush=True)
        return True
    except Exception as exc:
        print("YOUTUBE COMMUNITY UNAVAILABLE:", type(exc).__name__, str(exc)[:250], flush=True)
        return False

def refresh_rss():
    db = load("web.json", "items")
    previous = {x.get("source"): x for x in db["items"] if x.get("source")}
    sources = tech_sources()
    cutoff = datetime.now(timezone.utc).date() - timedelta(days=14)
    with ThreadPoolExecutor(max_workers=6) as executor:
        fetched = list(executor.map(lambda source: rss_card_for_source(source, cutoff), sources))
    count = 0
    updated = []
    for source, item in zip(sources, fetched):
        current = previous.get(source["name"])
        # Do not publish the same old RSS headline again and again.
        # A feed failure retains the prior successful snapshot.
        if item and (not current or item.get("date", "") >= current.get("date", "")):
            changed = not current or any(
                item.get(field) != current.get(field)
                for field in ("url", "title", "date")
            )
            if current and current.get("url") == item.get("url") and not item.get("image"):
                item["image"] = current.get("image", "")
            if changed:
                previous[source["name"]] = item
                count += 1
        if previous.get(source["name"]):
            updated.append(previous[source["name"]])
    if count:
        db["items"] = updated
        db["updated"] = datetime.now(timezone.utc).date().isoformat()
        save("web.json", db)
    print("EXTERNAL RSS: truly new headlines", count, "of", len(sources), flush=True)
    for item in updated:
        print("  rss", item["source"], item.get("date"), item.get("title", "")[:100], flush=True)
    return count > 0

def main():
    video_ok = youtube_videos()
    community_ok = youtube_community()
    rss_ok = refresh_rss()
    print("RECOVERY SOURCE STATUS:", {"videos": video_ok, "community": community_ok, "external_rss": rss_ok}, flush=True)
    if not (video_ok or community_ok or rss_ok):
        raise SystemExit("No live source reachable; refusing to claim a fresh import")

if __name__ == "__main__":
    main()
