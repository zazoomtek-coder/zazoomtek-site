import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import category_for_post
from article_routes import CATEGORY_PREFIX


class EditorialCategoryPrefixTests(unittest.TestCase):
    def test_review_gaming_prefix_overrides_stale_metadata(self):
        row = {
            "title": "Review Gaming: PAYDAY: ACES HIGH | Recensione PCVR",
            "type": "review",
            "topic": "tech",
            "category": "news-tech",
            "text_complete": True,
        }
        category = category_for_post(row)
        self.assertEqual(category, "recensioni-gaming")
        self.assertEqual(CATEGORY_PREFIX[category], "recensioni")

    def test_review_tech_prefix_overrides_stale_metadata(self):
        row = {
            "title": "Review Tech: Auricolari wireless",
            "type": "news",
            "topic": "gaming",
            "category": "news-gaming",
            "text_complete": True,
        }
        category = category_for_post(row)
        self.assertEqual(category, "recensioni-tech")
        self.assertEqual(CATEGORY_PREFIX[category], "recensioni")


if __name__ == "__main__":
    unittest.main()
