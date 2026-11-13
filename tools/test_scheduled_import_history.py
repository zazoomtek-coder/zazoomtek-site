import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scheduled_editorial_import as scheduled
import emergency_sync
import json


class HistoricalImportIsolationTests(unittest.TestCase):
    def test_scheduled_import_uses_archive_ids_as_optional_hints(self):
        def fake_snapshot(name, key):
            if name == "community_full.json":
                return {"posts": [{"id": "old-archive-id"}]}
            if name == "community.json":
                raise ValueError("corrupt historical snapshot")
            raise AssertionError(name)

        with patch.object(scheduled, "snapshot", side_effect=fake_snapshot):
            self.assertEqual(scheduled._historical_community_ids(), {"old-archive-id"})

    def test_import_manifest_is_valid_json_and_contains_only_new_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = scheduled.write_import_manifest(tmp, ["new-post", "new-post"], ["new-video"])
            stored = json.loads(Path(tmp, ".editorial-import-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(stored["strict_ids"], ["new-post", "new-video"])
        self.assertEqual(manifest["community_ids"], ["new-post"])
        self.assertEqual(manifest["video_ids"], ["new-video"])

    def test_youtube_community_import_survives_broken_historical_archives(self):
        imported = {"posts": []}
        saved = {}

        def fake_load(name, key):
            if name == "community_imported.json":
                return imported
            if name in ("community_full.json", "community.json"):
                raise ValueError("corrupt old archive")
            if name in ("posts.json", "studio_posts.json"):
                return {"posts": []}
            raise AssertionError(name)

        candidate = {
            "id": "Ugkxxxxxxxxxxxxxxxx",
            "title": "News Tech: nuovo contenuto YouTube valido",
            "text": "Questo è un post completo di prova. " * 8,
            "text_complete": True,
            "date": "2026-11-13",
            "type": "news",
        }

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(emergency_sync, "DATA", Path(tmp)), \
                 patch.object(emergency_sync, "load", side_effect=fake_load), \
                 patch.object(emergency_sync, "discover", return_value=[candidate]), \
                 patch.object(emergency_sync, "category_for_post", return_value="news-tech"), \
                 patch.object(emergency_sync, "save",
                              side_effect=lambda name, value: saved.update({name: value}) or True):
                self.assertTrue(emergency_sync.youtube_community())

        self.assertIn("community_imported.json", saved)
        self.assertEqual(len(saved["community_imported.json"]["posts"]), 1)
        result = saved["community_imported.json"]["posts"][0]
        self.assertEqual(result["id"], candidate["id"])
        self.assertEqual(result["route_version"], 2)
        self.assertEqual(result["public_path"].split("/")[1], "news")

if __name__ == "__main__":
    unittest.main()
