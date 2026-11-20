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
import time
import xml.etree.ElementTree as ET

from community_youtube import discover, date_from_relative
from sync_videos import CHANNEL_ID, NS, classify, is_short_entry, is_short_title
from build import tech_sources, rss_card_for_source, category_for_post
from article_routes import CATEGORY_PREFIX, unique_slug
from article_templates import author_for_category

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

def _community_plain_text(row):
    """Return comparable editorial text from legacy, Community and Studio records."""
    parts = [str(row.get("title") or ""), str(row.get("text") or ""),
             str(row.get("description") or "")]
    body = row.get("body")
    if isinstance(body, str):
        parts.append(body)
    elif isinstance(body, list):
        for block in body:
            if isinstance(block, dict):
                parts.append(str(block.get("text") or block.get("content") or ""))
            elif isinstance(block, str):
                parts.append(block)
    return " ".join(parts)


def _community_normalize(value):
    value = str(value or "").casefold()
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"https?://\S+", " ", value)
    value = re.sub(r"[^a-z0-9à-ÿ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _community_is_near_duplicate(candidate, published_rows):
    """Conservatively block the same editorial story, even when YouTube IDs differ."""
    from difflib import SequenceMatcher

    candidate_title = _community_normalize(candidate.get("title"))
    candidate_text = _community_normalize(_community_plain_text(candidate))
    if len(candidate_text) < 180:
        return False, None
    candidate_words = set(candidate_text.split())
    for current in published_rows:
        if not isinstance(current, dict):
            continue
        current_text = _community_normalize(_community_plain_text(current))
        if len(current_text) < 180:
            continue
        current_title = _community_normalize(current.get("title"))
        title_ratio = SequenceMatcher(None, candidate_title, current_title).ratio() if candidate_title and current_title else 0
        body_ratio = SequenceMatcher(None, candidate_text[:12000], current_text[:12000]).ratio()
        current_words = set(current_text.split())
        union = candidate_words | current_words
        word_overlap = len(candidate_words & current_words) / len(union) if union else 0
        # Require substantial body overlap as well as a similar title, OR
        # very high full-text similarity. This avoids blocking same-topic updates.
        if (title_ratio >= 0.90 and (body_ratio >= 0.48 or word_overlap >= 0.55)) or body_ratio >= 0.84 or word_overlap >= 0.78:
            return True, str(current.get("title") or current.get("slug") or current.get("id") or "articolo già pubblicato")
    return False, None


def _published_community_comparison_rows():
    """Load all available published article collections for duplicate screening."""
    rows = []
    for filename, key in (("posts.json", "posts"), ("studio_posts.json", "posts"),
                          ("community_imported.json", "posts"),
                          ("community_full.json", "posts"), ("community.json", "posts")):
        try:
            records = load(filename, key).get(key, [])
            if isinstance(records, list):
                rows.extend(record for record in records if isinstance(record, dict))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            print("WARNING: duplicate screening archive unavailable:",
                  filename, type(exc).__name__, str(exc)[:120], flush=True)
    try:
        overrides = json.loads((DATA / "studio_overrides.json").read_text(encoding="utf-8")).get("overrides", {})
        if isinstance(overrides, dict):
            rows.extend(record for record in overrides.values() if isinstance(record, dict))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("WARNING: Studio overrides unavailable for duplicate screening:",
              type(exc).__name__, str(exc)[:120], flush=True)
    return rows

def classify_upload(title):
    # Mantiene la classificazione storica: esclude soltanto gli YouTube Shorts.
    if is_short_title(title):
        return None
    original = classify(title)
    if original:
        return original
    low = title.casefold()
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
        xml = None
        last_error = None
        for attempt in range(3):
            try:
                request = urllib.request.Request(
                    url, headers={"User-Agent": "Mozilla/5.0 (compatible; ZazoomTek/1.0)"})
                with urllib.request.urlopen(request, timeout=25) as response:
                    xml = ET.fromstring(response.read(2_000_000))
                break
            except Exception as error:
                last_error = error
                if attempt < 2:
                    time.sleep(1 + attempt)
        if xml is None:
            raise RuntimeError("YouTube video RSS unavailable after 3 attempts") from last_error
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
            if is_short_entry(item):
                continue
            kindtopic = classify_upload(title)
            if not kindtopic:
                continue
            kind, topic = kindtopic
            known[video_id] = {"id": video_id, "title": title, "date": published_at, "topic": topic, "kind": kind}
            count += 1
        db["videos"] = sorted(known.values(), key=lambda x: x.get("date", ""), reverse=True)
        save("videos.json", db)
        print("YOUTUBE RSS: available, added", count, "valid channel videos (all non-Short uploads); recent uploads:", len(recent), flush=True)
        for date, title in recent[:18]:
            print("  video", date, title[:145], flush=True)
        return True
    except Exception as exc:
        print("YOUTUBE RSS UNAVAILABLE:", type(exc).__name__, str(exc)[:230], flush=True)
        return False

def youtube_community():
    db = load("community_imported.json", "posts")
    existing = {r.get("id"): r for r in db["posts"] if r.get("id")}
    # Historical archives are optional duplicate hints. A damaged old snapshot
    # must never make a valid current YouTube post unavailable for import.
    archived_ids = set()
    for filename in ("community_full.json", "community.json"):
        try:
            historical = load(filename, "posts")["posts"]
            archived_ids.update(x.get("id") for x in historical
                                if isinstance(x, dict) and x.get("id"))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            print("WARNING: ignoring unavailable historical archive during import:",
                  filename, type(exc).__name__, str(exc)[:160], flush=True)
    occupied_paths = set()
    for filename, key in (("posts.json", "posts"), ("studio_posts.json", "posts"),
                          ("community_imported.json", "posts"), ("community_full.json", "posts"),
                          ("community.json", "posts")):
        try:
            records = load(filename, key)[key]
        except (OSError, ValueError, KeyError, TypeError) as exc:
            print("WARNING: ignoring unavailable legacy slug registry:",
                  filename, type(exc).__name__, str(exc)[:120], flush=True)
            records = []
        occupied_paths.update(str(x.get("public_path")) for x in records
                              if isinstance(x, dict) and x.get("public_path"))
    try:
        overrides = json.loads((DATA / "studio_overrides.json").read_text(encoding="utf-8")).get("overrides", {})
    except (OSError, ValueError, TypeError):
        overrides = {}
    if isinstance(overrides, dict):
        occupied_paths.update(str(x.get("public_path")) for x in overrides.values()
                              if isinstance(x, dict) and x.get("public_path"))
    today = datetime.now(timezone.utc).date().isoformat()
    try:
        items = discover(limit=180, max_pages=15)
        added = []
        comparison_rows = _published_community_comparison_rows()
        duplicate_skipped = 0
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
            duplicate, matched_title = _community_is_near_duplicate(row, comparison_rows)
            if duplicate:
                duplicate_skipped += 1
                print("YOUTUBE COMMUNITY DUPLICATE SKIPPED:", row.get("title", "")[:120],
                      "matches:", matched_title[:120], flush=True)
                continue
            row = dict(row)
            category = category_for_post(row)
            prefix = CATEGORY_PREFIX.get(category)
            if not prefix:
                raise ValueError("Nuovo post Community senza categoria pubblica valida: " + str(category))
            public_slug = unique_slug(row.get("title") or "", occupied_paths, prefix=prefix)
            row["category"] = category
            row["author"] = author_for_category(category)
            row["route_version"] = 2
            row["public_slug"] = public_slug
            row["public_path"] = "/" + prefix + "/" + public_slug
            occupied_paths.add(row["public_path"])
            existing[post_id] = row
            added.append(row)
            comparison_rows.append(row)
        db["posts"] = sorted(existing.values(),
                             key=lambda p: p.get("published_at") or p.get("date") or "",
                             reverse=True)
        save("community_imported.json", db)
        print("YOUTUBE COMMUNITY: verified recent records", len(items),
              "new full posts", len(added), "near-duplicates skipped", duplicate_skipped,
              "total imported", len(db["posts"]), flush=True)
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
