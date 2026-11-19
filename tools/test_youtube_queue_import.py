import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from queue_collect import classify_upload, load


class YouTubeQueueImportTests(unittest.TestCase):
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
                self.assertEqual(classify_upload(title), expected)

    def test_shorts_are_not_promoted_to_video_archive(self):
        self.assertEqual(classify_upload("ZazoomTek Shorts"), ("short", "general"))

    def test_damaged_queue_snapshot_is_not_silently_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "queue_videos.json"
            path.write_text("{broken", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                load(path.name, "videos")


if __name__ == "__main__":
    unittest.main()
