#!/usr/bin/env python3
"""Offline regression tests for the YouTube Community and channel-video importers."""
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

import community_youtube
import emergency_sync


POST_ID = "UgkxRegressionTestPost123456789"
POST_TEXT = (
    "News Tech: Nuovo aggiornamento tecnologico per il canale ZazoomTek\n\n"
    "Questo testo completo di prova verifica il recupero del contenuto originale "
    "della Community, la data, la copertina e il salvataggio nell'archivio editoriale. "
    "La procedura deve conservare il testo integrale senza inventare informazioni."
)


def youtube_page(text=POST_TEXT):
    renderer = {
        "backstagePostRenderer": {
            "postId": POST_ID,
            "contentText": {"runs": [{"text": text}]},
            "publishedTimeText": {"simpleText": "2 giorni fa"},
            "backstageAttachment": {
                "thumbnails": [{"url": "https://i.ytimg.com/vi/example/hqdefault.jpg"}]
            },
        }
    }
    return "var ytInitialData = " + json.dumps({"contents": [renderer]}) + ";"


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, _limit=-1):
        return self.body


class YouTubeImportTests(unittest.TestCase):
    def test_community_discovery_recovers_full_original_post(self):
        with patch.object(community_youtube, "fetch", side_effect=lambda *a, **k: youtube_page()):
            posts = community_youtube.discover(limit=10, max_pages=2)
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["id"], POST_ID)
        self.assertEqual(posts[0]["text"], POST_TEXT)
        self.assertTrue(posts[0]["text_complete"])
        self.assertTrue(posts[0]["verified_detail"])
        self.assertTrue(posts[0]["image"].startswith("https://"))
        self.assertTrue(posts[0]["date"])

    def test_community_import_writes_verified_post_without_losing_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "community_imported.json").write_text(
                json.dumps({"posts": []}), encoding="utf-8")
            post = {
                "id": POST_ID, "title": POST_TEXT.splitlines()[0],
                "text": POST_TEXT, "date": "2026-11-19",
                "published_at": "2026-11-19T12:00:00+00:00",
                "type": "news", "text_complete": True,
                "image": "https://i.ytimg.com/vi/example/hqdefault.jpg",
            }
            with patch.object(emergency_sync, "DATA", root), \
                 patch.object(emergency_sync, "discover", return_value=[post]):
                self.assertTrue(emergency_sync.youtube_community())
            saved = json.loads((root / "community_imported.json").read_text(encoding="utf-8"))
            self.assertEqual(len(saved["posts"]), 1)
            self.assertEqual(saved["posts"][0]["id"], POST_ID)
            self.assertEqual(saved["posts"][0]["category"], "news-tech")
            self.assertEqual(saved["posts"][0]["text"], POST_TEXT)

    def test_community_source_failure_preserves_last_valid_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = {"posts": [{"id": POST_ID, "title": "Articolo già importato"}]}
            path = root / "community_imported.json"
            path.write_text(json.dumps(original), encoding="utf-8")
            with patch.object(emergency_sync, "DATA", root), \
                 patch.object(emergency_sync, "discover", side_effect=RuntimeError("YouTube unavailable")):
                self.assertFalse(emergency_sync.youtube_community())
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), original)

    def test_channel_rss_imports_regular_videos_and_excludes_shorts(self):
        atom = "http://www.w3.org/2005/Atom"
        yt = "http://www.youtube.com/xml/schemas/2015"
        ET.register_namespace("atom", atom)
        ET.register_namespace("yt", yt)
        root = ET.Element("{%s}feed" % atom)
        for video_id, title, short in (
            ("abcdefghijk", "Nuovo video ZazoomTek", False),
            ("lmnopqrstuv", "Shorts ZazoomTek", True),
        ):
            entry = ET.SubElement(root, "{%s}entry" % atom)
            ET.SubElement(entry, "{%s}videoId" % yt).text = video_id
            ET.SubElement(entry, "{%s}title" % atom).text = title
            ET.SubElement(entry, "{%s}published" % atom).text = "2026-11-19T12:00:00+00:00"
            if short:
                ET.SubElement(entry, "{%s}link" % atom, {"href": "https://www.youtube.com/shorts/" + video_id})
        xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp)
            (data / "videos.json").write_text(json.dumps({"videos": []}), encoding="utf-8")
            with patch.object(emergency_sync, "DATA", data), \
                 patch("emergency_sync.urllib.request.urlopen", return_value=FakeResponse(xml)):
                self.assertTrue(emergency_sync.youtube_videos())
            saved = json.loads((data / "videos.json").read_text(encoding="utf-8"))
            ids = {row["id"] for row in saved["videos"]}
            self.assertIn("abcdefghijk", ids)
            self.assertNotIn("lmnopqrstuv", ids)


if __name__ == "__main__":
    unittest.main(verbosity=2)
