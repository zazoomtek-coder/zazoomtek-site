import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from community_youtube import title_type


class YouTubeCommunityTitleTypeTests(unittest.TestCase):
    def test_current_guide_prefix_is_importable(self):
        title, kind = title_type("News Guida: Come configurare il Wi-Fi")
        self.assertEqual(kind, "guide")
        self.assertEqual(title, "News Guida: Come configurare il Wi-Fi")

    def test_current_special_prefix_is_importable(self):
        title, kind = title_type("News Speciale: Le novità del gaming")
        self.assertEqual(kind, "speciali")
        self.assertEqual(title, "News Speciale: Le novità del gaming")

    def test_existing_news_and_review_prefixes_remain_supported(self):
        self.assertEqual(title_type("News Tech: Nuovo smartphone")[1], "news")
        self.assertEqual(title_type("Review Gaming: Nuovo gioco")[1], "review")


if __name__ == "__main__":
    unittest.main()
