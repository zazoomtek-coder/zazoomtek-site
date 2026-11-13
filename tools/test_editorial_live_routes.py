import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_editorial_live import live_article_route


class EditorialLiveRouteTests(unittest.TestCase):
    def test_new_community_review_uses_nested_review_route(self):
        row = {
            "id": "UgkxBM-IBk3jEbR4kRltNewhwKmVceFa96nn",
            "title": "Review Gaming: PAYDAY: ACES HIGH | Recensione PCVR",
            "category": "recensioni-gaming",
            "route_version": 2,
            "public_slug": "review-gaming-payday-aces-high-recensione-pcvr",
            "public_path": "/recensioni/payday-aces-high-pcvr",
        }
        self.assertEqual(
            live_article_route(row),
            "/recensioni/payday-aces-high-pcvr",
        )

    def test_legacy_community_route_remains_flat(self):
        row = {
            "title": "Articolo storico",
            "legacy_path": "/community-ugkxrvwng0aanuqnw2w-cqhip06jqlklaktr",
        }
        self.assertEqual(
            live_article_route(row),
            "/community-ugkxrvwng0aanuqnw2w-cqhip06jqlklaktr",
        )

    def test_studio_override_uses_its_persisted_v2_path(self):
        row = {
            "title": "Guida router",
            "route_version": 2,
            "category": "guide",
            "public_slug": "configurare-router",
            "public_path": "/guide/configurare-router",
        }
        self.assertEqual(live_article_route(row, "old-studio-slug"), "/guide/configurare-router")

    def test_legacy_studio_slug_is_used_as_fallback(self):
        self.assertEqual(live_article_route({"title": "Legacy"}, "old-studio-slug"),
                         "/old-studio-slug")


if __name__ == "__main__":
    unittest.main()
