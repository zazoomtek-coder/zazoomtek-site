#!/usr/bin/env python3
"""Prove written Community publication and verified video publication are isolated."""
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory

BASE=Path(__file__).resolve().parent

def load(label, name):
    spec=importlib.util.spec_from_file_location(label, BASE/name)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

community=load("community_pages_isolated","03-home.py")
video=load("video_pages_isolated","02-video-pages.py")

def main():
    with TemporaryDirectory() as temp:
        root=Path(temp)
        (root/"services10-data").mkdir()
        (root/"services10-data"/"community.json").write_text(json.dumps([{
            "id":"UgkxOnlyWords123","text":"News Tech: Solo testo\\nParagrafo sul nuovo dispositivo.",
            "first_seen":"2026-10-23T08:00:00Z","image":""}]))
        (root/"news.html").write_text(
            '<html><body><article class="news-row">Existing</article></body></html>')
        (root/"index.html").write_text(
            '<html><body><!-- ARTICLE_FEED_START --><article class="article-row">Existing</article>'
            '<!-- ARTICLE_FEED_END --></body></html>')
        out=community.update(root)
        assert out["created_pages"]==1
        assert (root/"news-UgkxOnlyWords123.html").exists()
        assert not (root/"watch").exists()
        assert not (root/"home-video-feed.json").exists()
    with TemporaryDirectory() as temp:
        root=Path(temp)
        (root/"services10-data").mkdir()
        (root/"services10-data"/"videos.json").write_text(json.dumps([{
            "id":"abcdef12345","title":"Verified horizontal video",
            "type":"landscape_video","verification":"owner_file_details_16x9"}]))
        (root/"home-video-feed.json").write_text("[]")
        out=video.sync_video_catalog(root)
        assert out["new_videos"]==1
        assert (root/"watch"/"abcdef12345.html").exists()
        assert not (root/"news.html").exists()
        assert not list(root.glob("news-Ugkx*.html"))
    print("PASS: Community and video page builders operate independently, even without each other's data")

if __name__=="__main__":
    main()
