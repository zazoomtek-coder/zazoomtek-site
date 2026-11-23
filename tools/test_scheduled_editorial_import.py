import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scheduled_editorial_import as importer


class CommunityQueueVerificationTests(unittest.TestCase):
    def test_legacy_queue_records_are_reverified_before_import(self):
        old = {"id": "Ugabcdefghijklm", "text": "Short excerpt"}
        full = {
            **old,
            "text": "Complete verified Community post with all paragraphs.",
            "verified_detail": True,
            "text_complete": True,
        }
        with patch.object(importer, "verify_post_details", return_value=[full]) as mocked:
            result = importer.verify_community_queue_rows([old], set(), set())
        mocked.assert_called_once_with([old])
        self.assertEqual(result, [full])

    def test_already_published_or_archived_ids_are_not_refetched(self):
        old = {"id": "Ugabcdefghijklm", "text": "Old queue excerpt"}
        with patch.object(importer, "verify_post_details") as mocked:
            result = importer.verify_community_queue_rows(
                [old], {"Ugabcdefghijklm"}, set()
            )
        self.assertEqual(result, [])
        mocked.assert_not_called()

        with patch.object(importer, "verify_post_details") as mocked:
            result = importer.verify_community_queue_rows(
                [old], set(), {"Ugabcdefghijklm"}
            )
        self.assertEqual(result, [])
        mocked.assert_not_called()

    def test_verified_full_queue_records_do_not_need_another_fetch(self):
        full = {
            "id": "Ugabcdefghijklm",
            "text": "Complete text",
            "verified_detail": True,
            "text_complete": True,
        }
        with patch.object(importer, "verify_post_details") as mocked:
            result = importer.verify_community_queue_rows([full], set(), set())
        self.assertEqual(result, [full])
        mocked.assert_not_called()

    def test_unavailable_detail_fails_closed(self):
        old = {"id": "Ugabcdefghijklm", "text": "Unverified excerpt"}
        with patch.object(importer, "verify_post_details", side_effect=RuntimeError("offline")):
            result = importer.verify_community_queue_rows([old], set(), set())
        self.assertEqual(result, [])

    def test_shorts_are_imported_from_the_persistent_video_queue(self):
        short = {
            "id": "abcdefghijk",
            "title": "ZazoomTek Shorts: prova rapida",
            "date": "2026-11-23T10:00:00+00:00",
            "url": "https://www.youtube.com/shorts/abcdefghijk",
            "kind": "short",
            "topic": "general",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "videos.json").write_text(json.dumps({"videos": []}), encoding="utf-8")
            with patch.object(importer, "DATA", root):
                with patch.object(importer, "read_queue", return_value=[short]):
                    added = importer.merge_queue("queue_videos.json", "videos.json", "videos", set())
            saved = json.loads((root / "videos.json").read_text(encoding="utf-8"))["videos"]
        self.assertEqual(len(added), 1)
        self.assertEqual(saved[0]["id"], "abcdefghijk")



if __name__ == "__main__":
    unittest.main()
