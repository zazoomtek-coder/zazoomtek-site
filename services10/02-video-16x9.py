#!/usr/bin/env python3
"""Independent YouTube collector: only confirmed horizontal 16:9 videos.

No media is downloaded. yt-dlp inspects YouTube's actual video-stream metadata,
NOT the dimensions of a player embed or a thumbnail. Unknown and vertical
videos are skipped individually, while earlier confirmed videos are retained.
"""
from __future__ import annotations
import json
import os
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "services10-data" / "videos.json"
CHANNEL = os.environ.get("ZT_YOUTUBE_CHANNEL_ID", "UCJs0ZT10hUiPRD0UZtUpI1Q")
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}

def collect(xml: bytes) -> list[dict]:
    root = ET.fromstring(xml)
    found = []
    for entry in root.findall("a:entry", NS):
        try:
            video_id = entry.findtext("yt:videoId", namespaces=NS)
            title = entry.findtext("a:title", namespaces=NS)
            published = entry.findtext("a:published", namespaces=NS)
            if video_id and title and published:
                found.append({"id": video_id, "title": title,
                              "published": published,
                              "url": "https://www.youtube.com/watch?v=" + video_id,
                              "type": "landscape_video"})
        except (TypeError, ValueError, AttributeError):
            continue
    return found

def stream_shape(info: dict) -> tuple[int, int] | None:
    """Read actual encoded video frame dimensions from available streams."""
    streams = []
    for item in [info] + (info.get("formats") or []):
        try:
            if not isinstance(item, dict) or item.get("vcodec") == "none":
                continue
            width, height = int(item.get("width")), int(item.get("height"))
            if width > 0 and height > 0:
                streams.append((width * height, width, height))
        except (TypeError, ValueError):
            continue
    if not streams:
        return None
    _, width, height = max(streams)
    return width, height

def is_landscape_16_9(info: dict) -> bool:
    """Unknown is never assumed horizontal; no duration-based Shorts heuristic."""
    if not isinstance(info, dict):
        return False
    if "/shorts/" in str(info.get("webpage_url") or "").lower():
        return False
    shape = stream_shape(info)
    return bool(shape and abs(shape[0] / shape[1] - 16 / 9) <= 0.045)

def verified_ids(entries: list[dict]) -> set[str]:
    try:
        import yt_dlp
    except ImportError:
        print("yt-dlp not installed; no new videos classified")
        return set()
    accepted = set()
    options = {"skip_download": True, "quiet": True, "no_warnings": True,
               "noplaylist": True, "socket_timeout": 18, "retries": 1,
               "extractor_retries": 1}
    with yt_dlp.YoutubeDL(options) as client:
        for entry in entries:
            try:
                info = client.extract_info(entry["url"], download=False)
                if is_landscape_16_9(info):
                    accepted.add(entry["id"])
                else:
                    print("Not verified 16:9, skipped:", entry["id"])
            except Exception as exc:
                # An inaccessible video cannot stop processing the next one.
                print("Cannot inspect video", entry.get("id"), ":", str(exc)[:130])
    return accepted

def merge(previous: list[dict], incoming: list[dict]) -> list[dict]:
    by_id = {}
    for item in previous + incoming:
        if (isinstance(item, dict) and item.get("id") and item.get("title")
                and item.get("type") == "landscape_video"):
            by_id[item["id"]] = item
    return sorted(by_id.values(), key=lambda x: x.get("published", ""), reverse=True)

def save(items: list[dict]) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                     dir=OUT.parent, delete=False) as stream:
        json.dump(items, stream, ensure_ascii=False, indent=2)
        name = stream.name
    os.replace(name, OUT)

def main() -> None:
    try:
        existing = json.loads(OUT.read_text(encoding="utf-8")) if OUT.is_file() else []
        if not isinstance(existing, list):
            existing = []
    except (ValueError, OSError):
        existing = []
    try:
        url = "https://www.youtube.com/feeds/videos.xml?channel_id=" + CHANNEL
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=30) as response:
            incoming = collect(response.read())
    except Exception as exc:
        print("RSS temporarily unavailable; prior archive remains:", str(exc)[:130])
        return
    allowed = verified_ids(incoming)
    selected = [entry for entry in incoming if entry["id"] in allowed]
    result = merge(existing, selected)
    if result != existing:
        save(result)
    print("New 16:9:", len(selected), "Known 16:9:", len(result),
          "Other/unknown skipped:", len(incoming) - len(selected))

if __name__ == "__main__":
    main()
