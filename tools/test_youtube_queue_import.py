import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import queue_collect


class YouTubeQueueImportTests(unittest.TestCase):
    classify_upload = staticmethod(queue_collect.classify_upload)
    def test_all_non_short_channel_uploads_are_kept(self):
        cases = {
            "DTNO.1 DT H03 Recensione": ("review", "tech"),
            "Call of Duty PS5 Gameplay": ("gameplay", "gaming"),
            "Wizard101 Launch Trailer": ("trailer", "gaming"),
            "Crazy Taxi World Tour": ("video", "general"),
            "70mai Dash Cam Unboxing": ("unboxing", "tech"),
        }
        for title, expected in cases.items():
            with self.subTest(title=title):
                self.assertEqual(queue_collect.classify_upload(title), expected)

    def test_shorts_are_not_promoted_to_video_archive(self):
        self.assertEqual(queue_collect.classify_upload("ZazoomTek Shorts"), ("short", "general"))

    def test_damaged_queue_snapshot_is_not_silently_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "queue_videos.json"
            path.write_text("{broken", encoding="utf-8")
            original = queue_collect.DATA
            try:
                queue_collect.DATA = Path(tmp)
                with self.assertRaises(RuntimeError):
                    queue_collect.load(path.name, "videos")
            finally:
                queue_collect.DATA = original


if __name__ == "__main__":
    unittest.main()
