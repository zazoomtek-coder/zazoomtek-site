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

from emergency_sync import youtube_videos, youtube_community, refresh_rss, category_for_post
from article_routes import CATEGORY_PREFIX, unique_slug

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
    occupied_paths = set()
    for filename in ("posts.json", "studio_posts.json", "community_imported.json", "community_full.json"):
        try:
            existing_rows = snapshot(filename, "posts").get("posts", [])
        except (OSError, ValueError, KeyError):
            existing_rows = []
        occupied_paths.update(str(x.get("public_path")) for x in existing_rows
                              if isinstance(x, dict) and x.get("public_path"))
    try:
        overrides = json.loads((DATA / "studio_overrides.json").read_text(encoding="utf-8")).get("overrides", {})
    except (OSError, ValueError, TypeError):
        overrides = {}
    if isinstance(overrides, dict):
        occupied_paths.update(str(x.get("public_path")) for x in overrides.values()
                              if isinstance(x, dict) and x.get("public_path"))
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
        if key == "posts":
            category = category_for_post(clean)
            prefix = CATEGORY_PREFIX.get(category)
            if not prefix:
                raise ValueError("Nuovo post Community in coda senza categoria valida: " + str(category))
            clean["category"] = category
            if clean.get("route_version") not in (2, "2", "v2") or not clean.get("public_path"):
                public_slug = unique_slug(clean.get("title") or "", occupied_paths, prefix=prefix)
                clean.update({"route_version": 2, "public_slug": public_slug,
                              "public_path": "/" + prefix + "/" + public_slug})
            occupied_paths.add(clean["public_path"])
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
                    occupied = set()
                    for source_name in ("posts.json", "studio_posts.json", "community_imported.json", "community_full.json"):
                        try:
                            source_rows = snapshot(source_name, "posts").get("posts", [])
                        except (OSError, ValueError, KeyError):
                            source_rows = []
                        occupied.update(str(r.get("public_path")) for r in source_rows
                                        if isinstance(r, dict) and r.get("public_path"))
                    try:
                        existing_overrides = json.loads((DATA / "studio_overrides.json").read_text(encoding="utf-8")).get("overrides", {})
                    except (OSError, ValueError, TypeError):
                        existing_overrides = {}
                    if isinstance(existing_overrides, dict):
                        occupied.update(str(r.get("public_path")) for r in existing_overrides.values()
                                        if isinstance(r, dict) and r.get("public_path"))
                    prefix = CATEGORY_PREFIX.get(item["category"])
                    if not prefix:
                        raise ValueError("Nuovo articolo Studio senza categoria pubblica valida: " + item["category"])
                    if item.get("route_version") not in (2, "2", "v2") or not item.get("public_path"):
                        public_slug = unique_slug(item.get("title") or "", occupied, prefix=prefix)
                        item.update({"route_version": 2, "public_slug": public_slug,
                                     "public_path": "/" + prefix + "/" + public_slug})
                    rows.insert(0, item)
                    indexed = {r["slug"]: i for i, r in enumerate(rows)
                               if isinstance(r, dict) and r.get("slug")}
                    changed = True
                    added += 1
                elif rows[idx] != item and _date_stamp(item) > _date_stamp(rows[idx]):
                    for field in ("route_version", "legacy_path", "public_slug", "public_path"):
                        if field in rows[idx]:
                            item[field] = rows[idx][field]
                        else:
                            item.pop(field, None)
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


def _historical_community_ids():
    """Best-effort duplicate hints; damaged legacy archives never stop imports."""
    ids = set()
    for filename in ("community_full.json", "community.json"):
        try:
            records = snapshot(filename, "posts")["posts"]
            ids.update(str(row.get("id")) for row in records
                       if isinstance(row, dict) and row.get("id"))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            print("WARNING: historical archive unavailable; continuing import:",
                  filename, type(exc).__name__, str(exc)[:140], flush=True)
    return ids


def main():
    community_before = snapshot("community_imported.json", "posts")["posts"]
    video_before = snapshot("videos.json", "videos")["videos"]
    before_community_ids = {str(row.get("id")) for row in community_before
                            if isinstance(row, dict) and row.get("id")}
    before_video_ids = {str(row.get("id")) for row in video_before
                        if isinstance(row, dict) and row.get("id")}
    before = {name: len(snapshot(name, key)[key]) for name, key in
              (("community_imported.json", "posts"), ("videos.json", "videos"))}
    # Old archive snapshots are duplicate hints only, never prerequisites.
    archive = _historical_community_ids()
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
    after_community = snapshot("community_imported.json", "posts")["posts"]
    after_videos = snapshot("videos.json", "videos")["videos"]
    after = {"community_imported.json": len(after_community), "videos.json": len(after_videos)}
    new_community_ids = sorted(str(row.get("id")) for row in after_community
                               if isinstance(row, dict) and row.get("id")
                               and str(row.get("id")) not in before_community_ids)
    new_video_ids = sorted(str(row.get("id")) for row in after_videos
                           if isinstance(row, dict) and row.get("id")
                           and str(row.get("id")) not in before_video_ids)
    manifest = {
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "community_ids": new_community_ids,
        "video_ids": new_video_ids,
        "strict_ids": sorted(set(new_community_ids + new_video_ids)),
    }
    (Path(__file__).resolve().parents[1] / ".editorial-import-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
    print("IMPORT RELEASE MANIFEST:", manifest, flush=True)
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
