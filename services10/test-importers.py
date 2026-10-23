#!/usr/bin/env python3
"""Offline regression checks. No network, keys, or live Cloudflare deploy."""
import importlib.util
import json
import sys
import types
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent

def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

community = load("service_community", "01-community.py")
videos = load("service_videos", "02-video-shorts.py")

def main():
    xml = b'''<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom"
    xmlns:yt="http://www.youtube.com/xml/schemas/2015">
      <entry><yt:videoId>good1</yt:videoId><title>Review</title>
        <published>2026-10-23T12:00:00Z</published></entry>
      <entry><yt:videoId>bad</yt:videoId><title>Broken</title></entry>
      <entry><yt:videoId>good2</yt:videoId><title>Gameplay</title>
        <published>2026-10-23T13:00:00Z</published></entry>
    </feed>'''
    parsed_videos = videos.collect(xml)
    assert [x["id"] for x in parsed_videos] == ["good1", "good2"]
    older = [{"id": "old", "title": "Prior video",
              "published": "2026-10-20T08:00:00Z", "type": "landscape_video"}]
    merged = videos.merge(older, parsed_videos)
    assert len(merged) == 3 and merged[0]["id"] == "good2"
    assert len(videos.merge(merged, parsed_videos)) == 3

    horizontal = {"webpage_url": "https://www.youtube.com/watch?v=good1",
                  "formats": [{"vcodec": "avc1", "width": 1920, "height": 1080}]}
    vertical = {"webpage_url": "https://www.youtube.com/watch?v=vertical",
                "formats": [{"vcodec": "avc1", "width": 1080, "height": 1920}]}
    shorts = dict(horizontal, webpage_url="https://www.youtube.com/shorts/short1")
    assert videos.is_landscape_16_9(horizontal)
    assert not videos.is_landscape_16_9(vertical)
    assert not videos.is_landscape_16_9(shorts)
    assert not videos.is_landscape_16_9({"formats": []})
    assert videos.stream_shape({"formats": [{"vcodec": "none"}]}) is None

    # One inaccessible video is isolated: the other landscape video is accepted.
    class FakeYDL:
        def __init__(self, options): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def extract_info(self, url, download):
            if "bad" in url: raise RuntimeError("Temporary YouTube failure")
            if "good2" in url: return vertical
            return horizontal
    sys.modules["yt_dlp"] = types.SimpleNamespace(YoutubeDL=FakeYDL)
    try:
        result = videos.verified_ids([
            {"id": "good1", "url": "https://www.youtube.com/watch?v=good1"},
            {"id": "bad", "url": "https://www.youtube.com/watch?v=bad"},
            {"id": "good2", "url": "https://www.youtube.com/watch?v=good2"}
        ])
        assert result == {"good1"}
    finally:
        sys.modules.pop("yt_dlp", None)

    # Braces and semicolons inside post texts do not truncate nested JSON.
    posts = {"contents": {
        "a": {"backstagePostRenderer": {"postId": "Ugkx123",
              "contentText": {"runs": [{"text": "Tech news }; safe"}]}}},
        "b": {"backstagePostRenderer": {"postId": "broken"}},
        "c": {"backstagePostRenderer": {"postId": "Ugkx456",
              "contentText": {"simpleText": "Gaming update"}}}}}
    raw = 'var ytInitialData = ' + json.dumps(posts) + ';'
    parsed_community = community.extract(raw)
    assert {x["id"] for x in parsed_community} == {"Ugkx123", "Ugkx456"}
    assert len(community.merge(parsed_community, parsed_community)) == 2
    assert community.extract("var ytInitialData = {malformed;") == []

    with TemporaryDirectory() as tmp:
        videos.OUT = Path(tmp) / "videos.json"
        videos.save(merged)
        assert json.loads(videos.OUT.read_text()) == merged
        # Atomic overwrite without losing older entries.
        videos.save(videos.merge(merged, parsed_videos))
        assert len(json.loads(videos.OUT.read_text())) == 3
    print("PASS: Community + verified landscape video imports survive bad items; Shorts excluded")

if __name__ == "__main__":
    main()
