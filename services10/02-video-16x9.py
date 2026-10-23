#!/usr/bin/env python3
"""YouTube Data API v3 + official RSS, with no scraping, cookies or yt-dlp.

Uses channels.list, playlistItems.list and videos.list; API key remains in
the environment, never a published file. YouTube's public API does NOT expose
source frame geometry. Only externally confirmed 16:9 IDs may enter the
published landscape_video archive. Other non-Short long-form uploads are
retained in a separate pending archive; Shorts and unverifiable entries never
become site videos. Loss of API access never erases existing publications.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "services10-data" / "videos.json"
PENDING = ROOT / "services10-data" / "pending-videos.json"
CHANNEL = os.environ.get("ZT_YOUTUBE_CHANNEL_ID", "UCJs0ZT10hUiPRD0UZtUpI1Q")
API_KEY = os.environ.get("YOUTUBE_API_KEY", "").strip()
API_BASE = "https://www.googleapis.com/youtube/v3/"
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
DURATION = re.compile(r"^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$")

def load(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []

def save(items: list[dict], path: Path | None = None) -> None:
    target = path or OUT
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                     dir=target.parent, delete=False) as stream:
        json.dump(items, stream, ensure_ascii=False, indent=2)
        temporary = stream.name
    os.replace(temporary, target)

def collect(xml: bytes) -> list[dict]:
    """RSS supplies candidates only. RSS cannot verify Shorts or aspect."""
    root = ET.fromstring(xml)
    result = []
    for entry in root.findall("a:entry", NS):
        vid = entry.findtext("yt:videoId", namespaces=NS)
        title = entry.findtext("a:title", namespaces=NS)
        published = entry.findtext("a:published", namespaces=NS)
        if vid and VIDEO_ID.fullmatch(vid) and title and published:
            result.append({"id": vid, "title": title, "published": published,
                           "url": "https://www.youtube.com/watch?v=" + vid})
    return result

def duration_seconds(iso: str) -> int | None:
    match = DURATION.fullmatch(iso or "")
    if not match or not any(match.groups()):
        return None
    days, hours, minutes, seconds = (int(n or 0) for n in match.groups())
    return days * 86400 + hours * 3600 + minutes * 60 + seconds

def request_api(endpoint: str, params: dict, *, key: str | None = None) -> dict:
    """Small official read-only API call. Never reveal the API key in errors."""
    secret = (key if key is not None else API_KEY)
    if not secret:
        raise RuntimeError("YOUTUBE_API_KEY secret unavailable")
    query = urllib.parse.urlencode({**params, "key": secret})
    req = urllib.request.Request(API_BASE + endpoint + "?" + query,
                                 headers={"Accept": "application/json",
                                          "User-Agent": "ZazoomTekSite/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=22) as resp:
            result = json.load(resp)
        if not isinstance(result, dict):
            raise ValueError("Unexpected YouTube API response")
        return result
    except urllib.error.HTTPError as exc:
        raise RuntimeError("YouTube Data API returned HTTP " + str(exc.code)) from None
    except urllib.error.URLError:
        raise RuntimeError("YouTube Data API network unavailable") from None

def rss_candidates(channel: str = CHANNEL) -> list[dict]:
    url = "https://www.youtube.com/feeds/videos.xml?" + urllib.parse.urlencode({"channel_id": channel})
    req = urllib.request.Request(url, headers={"User-Agent": "ZazoomTekSite/1.0"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return collect(resp.read())

def upload_candidates(channel: str = CHANNEL, pages: int = 2) -> list[dict]:
    """Read official uploads playlist, avoiding expensive search.list calls."""
    channel_data = request_api("channels", {"part": "contentDetails", "id": channel})
    items = channel_data.get("items") or []
    if not items:
        raise RuntimeError("Channel not returned by YouTube API")
    playlist = (items[0].get("contentDetails") or {}).get("relatedPlaylists", {}).get("uploads")
    if not playlist:
        raise RuntimeError("YouTube uploads playlist unavailable")
    candidates = []
    token = ""
    for _ in range(max(1, min(pages, 4))):
        params = {"part": "snippet,contentDetails", "playlistId": playlist, "maxResults": 50}
        if token:
            params["pageToken"] = token
        data = request_api("playlistItems", params)
        for item in data.get("items") or []:
            details = item.get("contentDetails") or {}
            snippet = item.get("snippet") or {}
            vid = details.get("videoId") or (snippet.get("resourceId") or {}).get("videoId")
            if not (isinstance(vid, str) and VIDEO_ID.fullmatch(vid)):
                continue
            candidates.append({"id": vid, "title": snippet.get("title") or "",
                               "published": details.get("videoPublishedAt") or snippet.get("publishedAt") or "",
                               "url": "https://www.youtube.com/watch?v=" + vid})
        token = data.get("nextPageToken") or ""
        if not token:
            break
    return candidates

def metadata(candidates: list[dict]) -> list[dict]:
    ids = list(dict.fromkeys(row["id"] for row in candidates
                             if isinstance(row, dict) and VIDEO_ID.fullmatch(str(row.get("id") or ""))))
    result = []
    for offset in range(0, len(ids), 50):
        batch = ids[offset:offset + 50]
        try:
            response = request_api("videos", {
                "part": "snippet,contentDetails,status",
                "id": ",".join(batch), "maxResults": 50})
            result.extend(response.get("items") or [])
        except Exception as exc:
            print("YouTube API metadata batch failed; other batches retained:", str(exc)[:100])
    return result

def confirmed_ids(root: Path = ROOT) -> set[str]:
    """Manually confirmed frame geometry; not inferred from thumbnail/player size."""
    env = os.environ.get("ZT_CONFIRMED_16X9_IDS", "")
    approved = {i.strip() for i in env.split(",") if VIDEO_ID.fullmatch(i.strip())}
    registry = root / "services10-data" / "confirmed-16x9.json"
    if registry.is_file():
        data = load(registry)
        approved.update(x["id"] for x in data if isinstance(x, dict)
                        and VIDEO_ID.fullmatch(str(x.get("id") or ""))
                        and x.get("confirmed") is True)
    return approved

def classify(item: dict, approved: set[str], channel: str = CHANNEL) -> tuple[str, dict | None]:
    """No inaccurate 16:9 claim from thumbnails or embed player dimensions."""
    vid = str(item.get("id") or "")
    snippet = item.get("snippet") or {}
    details = item.get("contentDetails") or {}
    status = item.get("status") or {}
    if not VIDEO_ID.fullmatch(vid) or snippet.get("channelId") != channel:
        return "other", None
    if snippet.get("liveBroadcastContent") in ("live", "upcoming"):
        return "other", None
    if status.get("privacyStatus") not in (None, "public"):
        return "other", None
    if status.get("embeddable") is False:
        return "other", None
    seconds = duration_seconds(details.get("duration") or "")
    if not seconds or seconds <= 0:
        return "other", None
    record = {"id": vid, "title": str(snippet.get("title") or ""),
              "published": str(snippet.get("publishedAt") or ""),
              "url": "https://www.youtube.com/watch?v=" + vid,
              "duration_seconds": seconds}
    if not record["title"]:
        return "other", None
    if vid in approved:
        record.update({"type": "landscape_video", "verification": "confirmed_16x9_registry"})
        return "landscape", record
    # Shorts can be up to 3 minutes and may be vertical or square.
    if seconds <= 180:
        return "short_or_unknown", None
    # Over 3 minutes proves "not a Short" under current platform rules;
    # it does NOT prove that a video is horizontal. Await confirmation.
    record.update({"type": "pending_landscape", "verification": "duration_over_3m_only",
                   "orientation": "unverified"})
    return "pending", record

def merge(previous: list[dict], incoming: list[dict]) -> list[dict]:
    by_id = {}
    for row in previous + incoming:
        if isinstance(row, dict) and row.get("id") and row.get("title") \
                and row.get("type") == "landscape_video":
            by_id[row["id"]] = row
    return sorted(by_id.values(), key=lambda x: x.get("published", ""), reverse=True)

def merge_pending(previous: list[dict], incoming: list[dict], approved: set[str]) -> list[dict]:
    by_id = {}
    for row in previous + incoming:
        if isinstance(row, dict) and row.get("id") and row.get("type") == "pending_landscape" \
                and row["id"] not in approved:
            by_id[row["id"]] = row
    return sorted(by_id.values(), key=lambda x: x.get("published", ""), reverse=True)

def run() -> dict:
    old = load(OUT)
    prior_pending = load(PENDING)
    candidates = []
    rss_ok = False
    if API_KEY:
        try:
            candidates = upload_candidates()
            print("Official uploads playlist video candidates:", len(candidates))
        except Exception as exc:
            print("Official uploads playlist unavailable; attempting RSS:", str(exc)[:105])
    try:
        rss = rss_candidates()
        rss_ok = True
        seen = {row["id"] for row in candidates}
        candidates.extend(row for row in rss if row["id"] not in seen)
        print("Official RSS candidates:", len(rss))
    except Exception as exc:
        print("RSS temporarily unavailable; keeping saved archive:", str(exc)[:105])
    if not API_KEY:
        print("YOUTUBE_API_KEY missing: cannot verify Shorts/orientation; no new videos published")
        return {"source": "no_api_key", "verified_new": 0, "pending_new": 0, "retained": len(old)}
    if not candidates:
        print("No candidates: keeping prior archive and previously pending videos")
        return {"source": "no_candidates", "verified_new": 0, "pending_new": 0, "retained": len(old)}
    approved = confirmed_ids()
    known = metadata(candidates)
    landscape, pending = [], []
    skips = 0
    for item in known:
        category, row = classify(item, approved)
        if category == "landscape":
            landscape.append(row)
        elif category == "pending":
            pending.append(row)
        else:
            skips += 1
    approved.update(row["id"] for row in old if isinstance(row, dict) and
                    row.get("type") == "landscape_video" and row.get("verification") in
                    ("confirmed_16x9_registry", "source_stream_geometry"))
    updated = merge(old, landscape)
    old_pending_ids = {row.get("id") for row in prior_pending if isinstance(row, dict)}
    new_pending = merge_pending(prior_pending, pending, approved)
    if updated != old:
        save(updated)
    if new_pending != prior_pending:
        save(new_pending, PENDING)
    print("Official API result: verified 16:9:", len(landscape),
          "pending horizontal verification:", len(new_pending),
          "new pending:", len([x for x in new_pending if x["id"] not in old_pending_ids]),
          "non-videos/Shorts:", skips, "RSS read:", rss_ok)
    return {"source": "youtube_data_api_v3", "verified_new": len(landscape),
            "pending_new": len(new_pending), "retained": len(updated)}

def main() -> None:
    run()

if __name__ == "__main__":
    main()
