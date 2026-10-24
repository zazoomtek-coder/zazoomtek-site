#!/usr/bin/env python3
"""YouTube Data API v3 + official RSS, with no scraping, cookies or yt-dlp.

Uses channels.list, playlistItems.list and videos.list; API key remains in
the environment, never a published file. YouTube's public API does NOT expose
source frame geometry. All public channel uploads can be indexed: confirmed 16:9 are marked
landscape, all others retain unknown aspect without falsely claiming 16:9.
Existing pending public uploads are included and deduplicated. No cookies/scraping or insecure duration-only fallback.
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

def rss_public_records(rows: list[dict]) -> list[dict]:
    """Preserve IDs surfaced in YouTube's public RSS if API metadata is limited."""
    found=[]
    for row in rows:
        if not isinstance(row,dict):continue
        vid=str(row.get("id") or "")
        if not VIDEO_ID.fullmatch(vid):continue
        found.append({"id":vid,"title":str(row.get("title") or "Video ZazoomTek"),
                      "published":str(row.get("published") or ""),
                      "url":"https://www.youtube.com/watch?v="+vid,
                      "type":"youtube_video","verification":"official_public_rss",
                      "orientation":"unverified","short":False,
                      "duration_seconds":0,"embeddable":True})
    return found

def upload_candidates(channel: str = CHANNEL, pages: int | None = None) -> list[dict]:
    """Read the uploads playlist with nextPageToken until exhausted.

    ZT_YOUTUBE_MAX_PAGES=3 bounds hourly incremental scans; setting it to 0
    performs full reconciliation (used daily). Archived older uploads survive
    every incremental run. API quota/outages are reported without data loss.
    """
    if pages is None:
        pages=int(os.environ.get("ZT_YOUTUBE_MAX_PAGES","3"))
    if pages < 0:
        raise ValueError("ZT_YOUTUBE_MAX_PAGES must be >= 0")
    channel_data = request_api("channels", {"part": "contentDetails", "id": channel})
    items = channel_data.get("items") or []
    if not items:
        raise RuntimeError("Channel not returned by YouTube API")
    playlist = (items[0].get("contentDetails") or {}).get("relatedPlaylists", {}).get("uploads")
    if not playlist:
        raise RuntimeError("YouTube uploads playlist unavailable")
    candidates = []
    token = ""
    page_no = 0
    while True:
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
        page_no += 1
        if not token or (pages and page_no >= pages):
            break
    print("YouTube uploads playlist pages scanned:",page_no,
          "full_sync:",pages == 0,"next_page_remaining:",bool(token))
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

def owner_geometry(items: list[dict]) -> dict[str, dict]:
    """Read source aspect from official owner-authorized fileDetails.

    A public API key cannot fetch this field. Optional OAuth secrets come
    from GitHub Actions only; no credentials appear in URLs/logs/artifacts.
    """
    client_id = os.environ.get("YOUTUBE_OAUTH_CLIENT_ID", "").strip()
    client_secret = os.environ.get("YOUTUBE_OAUTH_CLIENT_SECRET", "").strip()
    refresh = os.environ.get("YOUTUBE_OAUTH_REFRESH_TOKEN", "").strip()
    if not (client_id and client_secret and refresh):
        print("Owner fileDetails unavailable: OAuth connection not configured")
        return {}
    body = urllib.parse.urlencode({
        "client_id": client_id, "client_secret": client_secret,
        "refresh_token": refresh, "grant_type": "refresh_token"
    }).encode("utf-8")
    try:
        req = urllib.request.Request("https://oauth2.googleapis.com/token", data=body,
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=20) as response:
            token = json.load(response).get("access_token")
        if not isinstance(token, str) or not token:
            raise ValueError("Missing access token")
    except Exception:
        print("Owner OAuth token unavailable; unknown orientations stay pending")
        return {}
    eligible_ids = [str(x.get("id")) for x in items if isinstance(x, dict)
                    and VIDEO_ID.fullmatch(str(x.get("id") or ""))
                    and (duration_seconds((x.get("contentDetails") or {}).get("duration") or "") or 0) > 180]
    by_id: dict[str, dict] = {}
    for start in range(0, len(eligible_ids), 50):
        batch = eligible_ids[start:start + 50]
        url = API_BASE + "videos?" + urllib.parse.urlencode({
            "part": "fileDetails", "id": ",".join(batch), "maxResults": 50
        })
        try:
            req = urllib.request.Request(
                url, headers={"Authorization": "Bearer " + token,
                              "Accept": "application/json",
                              "User-Agent": "ZazoomTekSite/1.0"})
            with urllib.request.urlopen(req, timeout=25) as response:
                result = json.load(response)
            for video in result.get("items") or []:
                if isinstance(video, dict) and video.get("id") in batch:
                    by_id[video["id"]] = video.get("fileDetails") or {}
        except Exception:
            print("Owner source geometry unavailable for batch; preserving queue")
    return by_id


def verified_16x9(file_details: dict) -> bool:
    """Require display aspect ratio 16:9. Vertical, square and 4:3 fail.

    Google documents aspectRatio as *display* aspect and width/height as
    encoded geometry. Use width/height only when rotation can be resolved.
    """
    if not isinstance(file_details, dict):
        return False
    streams = file_details.get("videoStreams")
    if not isinstance(streams, list) or not streams:
        return False
    shapes = []
    for stream in streams:
        if not isinstance(stream, dict):
            continue
        try:
            rotation = str(stream.get("rotation") or "none")
            aspect = stream.get("aspectRatio")
            if aspect is not None:
                ratio = float(aspect)
            else:
                width = int(stream.get("widthPixels"))
                height = int(stream.get("heightPixels"))
                if width <= 0 or height <= 0 or rotation not in (
                        "none", "clockwise", "counterClockwise", "upsideDown"):
                    return False
                ratio = (height / width) if rotation in (
                    "clockwise", "counterClockwise") else (width / height)
            if not (ratio > 0):
                return False
            shapes.append(ratio)
        except (ValueError, TypeError, OverflowError, ZeroDivisionError):
            return False
    # Reject mixed orientations and unverifiable streams.
    return bool(shapes) and all(abs(ratio - (16 / 9)) <= 0.025 for ratio in shapes)


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

def classify(item: dict, approved: set[str], channel: str = CHANNEL,
             geometry: dict[str, dict] | None = None) -> tuple[str, dict | None]:
    """Catalog all public channel uploads; classify their format without excluding them."""
    vid = str(item.get("id") or "")
    snippet = item.get("snippet") or {}
    details = item.get("contentDetails") or {}
    status = item.get("status") or {}
    if not VIDEO_ID.fullmatch(vid) or snippet.get("channelId") not in (None,channel):
        return "other", None
    # Only actually public uploads can be mirrored: private/deleted or
    # unlisted owner content is not a public channel publication.
    if status.get("privacyStatus") not in (None, "public"):
        return "other", None
    seconds = duration_seconds(details.get("duration") or "") or 0
    live_status=str(snippet.get("liveBroadcastContent") or "none")
    is_short = bool(seconds > 0 and seconds <= 180 and live_status=="none")
    record = {"id": vid, "title": str(snippet.get("title") or "Video ZazoomTek"),
              "published": str(snippet.get("publishedAt") or ""),
              "url": "https://www.youtube.com/watch?v=" + vid,
              "duration_seconds": seconds, "short": is_short,
              "live": live_status, "embeddable": status.get("embeddable") is not False}
    # Live/upcoming and duration-unknown public records must be indexed, even
    # when YouTube does not yet report a final duration/frame geometry.
    if live_status in ("live","upcoming") or seconds==0:
        record.update({"type":"youtube_video","verification":"official_youtube_metadata",
                       "orientation":"unverified"})
        return "youtube",record
    if is_short:
        record.update({"type": "youtube_video", "verification": "official_youtube_metadata",
                       "orientation": "unverified"})
        return "youtube", record
    source_details = (geometry or {}).get(vid)
    if source_details is not None:
        # Owner-provided geometry takes precedence over any stale registry.
        if not verified_16x9(source_details):
            record.update({"type": "youtube_video", "verification": "official_youtube_metadata",
                           "orientation": "not_16x9"})
            return "youtube", record
        record.update({"type": "landscape_video", "verification": "owner_file_details_16x9",
                       "orientation": "16:9_confirmed"})
        return "landscape", record
    if vid in approved:
        record.update({"type": "landscape_video", "verification": "confirmed_16x9_registry",
                       "orientation": "16:9_confirmed"})
        return "landscape", record
    record.update({"type": "youtube_video", "verification": "official_youtube_metadata",
                   "orientation": "unverified"})
    return "youtube", record

def merge(previous: list[dict], incoming: list[dict]) -> list[dict]:
    by_id = {}
    for row in previous + incoming:
        if isinstance(row, dict) and row.get("id") and row.get("title") \
                and row.get("type") in ("landscape_video", "youtube_video"):
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
    previous = load(OUT)
    prior_pending = load(PENDING)
    # Quarantine records imported by the former duration-only rule, never
    # quietly treat "orientation=unverified" as already confirmed 16:9.
    unsafe = [row for row in previous if isinstance(row, dict) and
              row.get("type") == "landscape_video" and
              (row.get("verification") == "duration_over_3m_not_short" or
               row.get("orientation") == "unverified")]
    old = [row for row in previous if row not in unsafe]
    if unsafe:
        for row in unsafe:
            if (isinstance(row.get("duration_seconds"), (int, float))
                and row["duration_seconds"] > 180 and row.get("id")):
                prior_pending.append({**row, "type": "pending_landscape",
                                      "verification": "duration_over_3m_only"})
        save(old)
        print("Quarantined unverified duration-only imports:", len(unsafe))
    candidates = []
    rss = []
    rss_ok = False
    if API_KEY:
        try:
            candidates = upload_candidates()
            print("Official uploads playlist candidates:", len(candidates))
        except Exception as exc:
            print("Official uploads playlist unavailable; trying RSS:", str(exc)[:105])
    try:
        rss = rss_candidates()
        rss_ok = True
        seen = {row["id"] for row in candidates}
        candidates.extend(row for row in rss if row["id"] not in seen)
        print("Official RSS candidates:", len(rss))
    except Exception:
        print("RSS unavailable; retaining prior archives")
    if not candidates:
        if unsafe:
            save(merge_pending(prior_pending, [], set()), PENDING)
        return {"source": "no_candidates", "verified_new": 0, "pending_new": len(prior_pending),
                "retained": len(old)}
    if not API_KEY:
        updated=merge(old,rss_public_records(rss))
        if updated!=previous:save(updated)
        if unsafe:save(merge_pending(prior_pending,[],set()),PENDING)
        print("YouTube API key missing; retained public RSS IDs without guessing duration")
        return {"source":"rss_without_metadata","verified_new":len(updated)-len(old),
                "pending_new":len(prior_pending),"retained":len(updated)}
    known = metadata(candidates)
    if not known:
        updated=merge(old,rss_public_records(rss))
        if updated!=previous:save(updated)
        if unsafe:save(merge_pending(prior_pending,[],set()),PENDING)
        print("YouTube metadata temporarily unavailable; saved IDs from public RSS")
        return {"source":"rss_metadata_fallback","verified_new":len(updated)-len(old),
                "pending_new":len(prior_pending),"retained":len(updated)}
    approved = confirmed_ids()
    geometry = owner_geometry(known)
    landscape, pending = [], []
    excluded = 0
    for item in known:
        category, row = classify(item, approved, geometry=geometry)
        if category in ("landscape", "youtube"):
            landscape.append(row)
        elif category == "pending":
            pending.append(row)
        else:
            excluded += 1
    # The former pending queue consists of real uploads previously returned by
    # the official API. Import them under a neutral type (no aspect claim).
    for archived in prior_pending:
        if not isinstance(archived, dict):
            continue
        vid = str(archived.get("id") or "")
        if not VIDEO_ID.fullmatch(vid) or not archived.get("title"):
            continue
        try:
            seconds = int(archived.get("duration_seconds") or 0)
        except (ValueError, TypeError):
            seconds = 0
        if seconds <= 0:
            continue
        landscape.append({**archived, "type": "youtube_video",
                          "verification": "official_youtube_metadata_archived",
                          "orientation": "unverified", "short": seconds <= 180})
    # Public RSS can include a brand-new upload missed by partial API batches.
    # Keep only genuine RSS IDs here; official metadata overwrites RSS values.
    landscape=merge(rss_public_records(rss),landscape)
    updated = merge(old, landscape)
    confirmed = {row["id"] for row in updated}
    queue = merge_pending(prior_pending, pending, confirmed)
    if updated != previous:
        save(updated)
    if queue != load(PENDING):
        save(queue, PENDING)
    print("Official API result: confirmed >180s and 16:9:", len(landscape),
          "pending aspect validation:", len(queue),
          "excluded unavailable/private/unembeddable:", excluded,
          "RSS read:", rss_ok)
    return {"source": "youtube_data_api_v3", "verified_new": len(landscape),
            "pending_new": len(queue), "retained": len(updated)}

def main() -> None:
    run()

if __name__ == "__main__":
    main()
