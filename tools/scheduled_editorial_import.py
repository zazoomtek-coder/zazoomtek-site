#!/usr/bin/env python3
"""ZazoomTek editorial import. Run before approved 12:30/16:00/19:30 releases.

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
            title = str(r.get("title") or "")
            link_values = " ".join(str(r.get(field) or "") for field in ("url", "link", "video_url"))
            if (re.search(r"(?:#|\b)shorts?\b|/shorts/", title + " " + link_values, re.IGNORECASE)
                    or "youtube.com/shorts/" in link_values.casefold()):
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




# Studio publishes approved articles and their media directly to main.
# editorial-queue is read ONLY as a backward-compatible source for older
# publications that may still be waiting there. Never import V2 drafts.
STUDIO_CATEGORIES = {
    "news-tech", "news-gaming", "extra", "speciali", "guide",
    "recensioni-tech", "recensioni-gaming",
}
STUDIO_CATEGORY_LABELS = {
    "news tech": "news-tech",
    "news gaming": "news-gaming",
    "news extra": "extra",
    "news speciali": "speciali",
    "news guide": "guide",
    "recensioni tech": "recensioni-tech",
    "recensioni gaming": "recensioni-gaming",
}
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _studio_category(row):
    category = str(row.get("category") or "").strip().lower().replace("_", " ").replace("-", " ")
    if category in STUDIO_CATEGORY_LABELS:
        return STUDIO_CATEGORY_LABELS[category]
    if category == "recensioni":
        kind = str(row.get("review_type") or row.get("subcategory") or "").strip().lower()
        if kind in ("tech", "gaming"):
            return "recensioni-" + kind
    return category.replace(" ", "-")


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
    if _studio_category(row) not in STUDIO_CATEGORIES or not row.get("image"):
        return False
    if not isinstance(row.get("title"), str) or len(row["title"]) < 12:
        return False
    body = row.get("body")
    if not isinstance(body, list) or not (1 <= len(body) <= 160):
        return False
    words = " ".join(str(b.get("text", "")) for b in body
                     if isinstance(b, dict) and b.get("type") in ("paragraph", "quote"))
    # Studio accepts an approved article with meaningful text; do not discard it
    # silently because it is shorter than an arbitrary 260-character limit.
    return len(words.strip()) >= 60


def sync_studio_publications():
    """Keep main as the authoritative Studio publication source.

    Studio's current save API writes published posts/overrides directly to
    main. The checked-out data files are therefore the primary source and are
    retained intact. editorial-queue is consulted only for legacy records;
    drafts are never read. Per-slug upsert prevents stale queue data replacing
    a newer main publication.
    """
    added = 0
    for filename, key in (("studio_posts.json", "posts"),
                          ("studio_overrides.json", "overrides")):
        queued = read_queue(filename, key) if key == "posts" else []
        path = DATA / filename
        old = json.loads(path.read_text(encoding="utf-8"))
        rows = old.get(key)
        if not isinstance(old, dict) or not isinstance(rows, list if key == "posts" else dict):
            raise ValueError("Invalid Studio publication snapshot: " + filename)
        changed = False
        if key == "posts":
            indexed = {r.get("slug"): i for i, r in enumerate(rows)
                       if isinstance(r, dict) and isinstance(r.get("slug"), str)}
            for item in queued:
                if not _valid_studio_row(item):
                    raise ValueError("Invalid approved Studio post in queue: " + str(item.get("slug", "<missing>")))
                item = dict(item)
                item["category"] = _studio_category(item)

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
                        raise ValueError("Invalid approved Studio override in queue: " + str(slug))
                    item = dict(item)
                    item["category"] = _studio_category(item)

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
    """Stage ONLY media referenced by explicitly published Studio articles.

    A media upload in editorial-queue may belong to an unapproved draft.
    Never copy it into the public release unless a published Studio post or
    override references that exact safe local media path.
    """
    root = DATA.parent
    safe = re.compile(r"^assets/uploads/[a-z0-9-]+/[a-z0-9-]+\.(?:jpg|jpeg|png|webp|mp3|m4a|wav|pdf|txt)$")
    referenced = set()
    for filename, key in (("studio_posts.json", "posts"),
                          ("studio_overrides.json", "overrides")):
        doc = json.loads((DATA / filename).read_text(encoding="utf-8"))[key]
        records = doc if isinstance(doc, list) else doc.values()
        for row in records:
            if not _valid_studio_row(row):
                continue
            for url in [row.get("image")] + [b.get("url") for b in row["body"] if isinstance(b, dict)]:
                if isinstance(url, str) and url.startswith("/assets/uploads/"):
                    candidate = url.lstrip("/")
                    if safe.fullmatch(candidate):
                        referenced.add(candidate)
    added = 0
    for name in sorted(referenced):
        target = root / name
        if target.is_file():
            continue
        try:
            blob = subprocess.check_output(
                ["git", "show", "origin/editorial-queue:" + name],
                stderr=subprocess.DEVNULL, timeout=15,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError("Published Studio media missing from release queue: " + name) from exc
        if not (0 < len(blob) <= 12000000):
            raise ValueError("Published Studio media size outside allowed range: " + name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)
        added += 1
    print("STUDIO ASSETS SYNC", added, "new media of",len(referenced),"approved media",flush=True)
    return added


def main():
    community_before = snapshot("community_imported.json", "posts")["posts"]
    before_community_ids = {str(row.get("id")) for row in community_before
                            if isinstance(row, dict) and row.get("id")}
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
    seo_result = {"optimized": 0, "skipped": 0, "failed": 0}
    try:
        from seo_editorial_optimizer import optimize_new_community_posts
        seo_result = optimize_new_community_posts(before_community_ids)
    except Exception as exc:
        print("SEO AI FAILED OPEN; original Community content preserved:",
              type(exc).__name__, str(exc)[:170], flush=True)
    after = {name: len(snapshot(name, key)[key]) for name, key in
             (("community_imported.json", "posts"), ("videos.json", "videos"))}
    print("IMPORT RESULT",
          "new Community:", after["community_imported.json"] - before["community_imported.json"],
          "new videos:", after["videos.json"] - before["videos.json"],
          "RSS OK:", results["rss"],
          "SEO AI:", seo_result,
          "Studio publications:", studio_updates, "Studio uploads:", studio_assets, flush=True)
    print("LIVE SOURCES:", results, flush=True)
    for p in snapshot("community_imported.json", "posts")["posts"][:8]:
        print("LATEST COMMUNITY", p.get("date"), str(p.get("title", ""))[:130], flush=True)
    # An unavailable source never causes a fictitious success claim; the
    # release decision is separately driven by real changed content files.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
