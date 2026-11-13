import unittest
from tools.article_routes import build_article_url, normalize_public_path, slugify_title, slugify_review_title, clean_category_slug, unique_slug, assign_public_routes

class ArticleRoutesTests(unittest.TestCase):
    def test_category_mapping(self):
        cases = {
            "recensioni-tech": "/recensioni/auricolari-wireless",
            "recensioni-gaming": "/recensioni/zelda-ocarina-time",
            "news-tech": "/news/nuovo-smartphone",
            "news-gaming": "/news/nuovo-videogioco",
            "speciali": "/speciali/guida-acquisto",
            "guide": "/guide/configurare-router",
            "extra": "/extra/approfondimento-tech",
        }
        for category, expected in cases.items():
            self.assertEqual(build_article_url({
                "route_version": "v2", "category": category,
                "public_slug": expected.rsplit("/", 1)[-1],
            }), expected)

    def test_category_slug_removes_only_leading_duplicate_labels(self):
        cases = {
            ("news-tech-funko-calendari-avvento-2026-disney-harry-potter", "news"):
                "funko-calendari-avvento-2026-disney-harry-potter",
            ("news-extra-funko-calendari-avvento-2026", "news"):
                "funko-calendari-avvento-2026",
            ("extra-extra-funko-calendari-avvento-2026", "extra"):
                "funko-calendari-avvento-2026",
            ("guide-guide-configurare-router", "guide"):
                "configurare-router",
            ("speciali-speciali-console", "speciali"):
                "console",
            ("recensioni-tech-xiaomi-buds", "recensioni"):
                "xiaomi-buds",
            ("funko-extra-edition", "extra"):
                "funko-extra-edition",
        }
        for (slug, category), expected in cases.items():
            self.assertEqual(clean_category_slug(slug, category), expected)

    def test_all_v2_categories_rewrite_duplicated_category_prefixes(self):
        rows = [
            {"route_version": 2, "category": "news-tech", "title": "Funko Calendari Avvento",
             "public_path": "/news/news-tech-funko-calendari-avvento-2026-disney-harry-potter"},
            {"route_version": 2, "category": "speciali", "title": "Console",
             "public_path": "/speciali/speciali-console"},
            {"route_version": 2, "category": "guide", "title": "Router",
             "public_path": "/guide/guide-configurare-router"},
            {"route_version": 2, "category": "extra", "title": "Funko",
             "public_path": "/extra/news-extra-funko-calendari-avvento-2026-disney-harry-potter"},
        ]
        assign_public_routes(rows)
        self.assertEqual(rows[0]["public_path"], "/news/funko-calendari-avvento-2026-disney-harry-potter")
        self.assertEqual(rows[1]["public_path"], "/speciali/console")
        self.assertEqual(rows[2]["public_path"], "/guide/configurare-router")
        self.assertEqual(rows[3]["public_path"], "/extra/funko-calendari-avvento-2026-disney-harry-potter")

    def test_build_article_url_cleans_legacy_category_labels(self):
        self.assertEqual(build_article_url({
            "route_version": 2, "category": "news-tech",
            "public_path": "/news/news-tech-smartphone-2026",
        }), "/news/smartphone-2026")
        self.assertEqual(build_article_url({
            "route_version": 2, "category": "extra",
            "public_path": "/extra/extra-funko-calendari-avvento-2026",
        }), "/extra/funko-calendari-avvento-2026")

    def test_review_slug_removes_editorial_prefix_and_suffix(self):
        self.assertEqual(
            slugify_review_title("Review Gaming: PAYDAY: ACES HIGH | Recensione PCVR"),
            "payday-aces-high-pcvr",
        )
        self.assertEqual(
            slugify_review_title("Review Tech: Xiaomi Buds | Recensione"),
            "xiaomi-buds",
        )

    def test_review_route_rewrites_existing_long_v2_path(self):
        rows = [{
            "route_version": 2, "category": "recensioni-gaming",
            "title": "Review Gaming: PAYDAY: ACES HIGH | Recensione PCVR",
            "public_slug": "review-gaming-payday-aces-high-recensione-pcvr",
            "public_path": "/recensioni/review-gaming-payday-aces-high-recensione-pcvr",
        }]
        assign_public_routes(rows)
        self.assertEqual(rows[0]["public_slug"], "payday-aces-high-pcvr")
        self.assertEqual(rows[0]["public_path"], "/recensioni/payday-aces-high-pcvr")
        self.assertEqual(build_article_url(rows[0]), "/recensioni/payday-aces-high-pcvr")

    def test_review_collision_gets_deterministic_suffix(self):
        rows = [
            {"route_version": 2, "category": "recensioni-tech",
             "title": "Review Tech: Xiaomi Buds | Recensione",
             "public_path": "/recensioni/old-xiaomi-buds"},
            {"route_version": 2, "category": "recensioni-gaming",
             "title": "Review Gaming: Xiaomi Buds | Recensione",
             "public_path": "/recensioni/old-xiaomi-buds-2"},
        ]
        assign_public_routes(rows)
        self.assertEqual(rows[0]["public_path"], "/recensioni/xiaomi-buds")
        self.assertEqual(rows[1]["public_path"], "/recensioni/xiaomi-buds-2")

    def test_explicit_legacy_path_is_immutable(self):
        path = "/community-ugkxrvwng0aanuqnw2w-cqhip06jqlklaktr"
        self.assertEqual(build_article_url({
            "legacy_path": path, "route_version": "v2",
            "category": "recensioni-gaming", "slug": "new-title",
        }), path)

    def test_historical_flat_slug_is_preserved_without_route_version(self):
        self.assertEqual(build_article_url({"slug": "recensione-storica"}), "/recensione-storica")

    def test_legacy_path_is_returned_exactly(self):
        path = "/old-article-path"
        self.assertEqual(build_article_url({"legacy_path": path}), path)

    def test_integer_route_version_is_supported(self):
        self.assertEqual(build_article_url({
            "route_version": 2, "category": "guide", "public_slug": "router-wifi"
        }), "/guide/router-wifi")

    def test_legacy_url_field_is_preserved(self):
        path = "/community-ugkxrvwng0aanuqnw2w-cqhip06jqlklaktr"
        self.assertEqual(build_article_url({"url": path}), path)

    def test_unknown_category_is_rejected(self):
        with self.assertRaises(ValueError):
            build_article_url({"route_version": "v2", "category": "blog", "slug": "test"})

    def test_trailing_slash_is_removed(self):
        self.assertEqual(normalize_public_path("/guide/prova/"), "/guide/prova")

    def test_slug_ascii_and_max_length(self):
        slug = slugify_title("È arrivata la nuova recensione: Auricolari! 2026")
        self.assertTrue(slug.isascii())
        self.assertLessEqual(len(slug), 68)
        self.assertRegex(slug, r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

    def test_incremental_collision_suffix(self):
        occupied = set()
        self.assertEqual(unique_slug("Nuovo smartphone", occupied), "smartphone")
        self.assertEqual(unique_slug("Nuovo smartphone", occupied), "smartphone-2")

    def test_category_scoped_slug_collision(self):
        occupied = {"/news/smartphone"}
        self.assertEqual(unique_slug("Nuovo smartphone", occupied, prefix="recensioni"),
                         "smartphone")
        self.assertEqual(unique_slug("Nuovo smartphone", occupied, prefix="news"),
                         "smartphone-2")

    def test_assign_routes_preserves_already_clean_existing_paths(self):
        rows = [
            {"route_version": 2, "category": "news-tech", "title": "Titolo cambiato",
             "public_slug": "titolo-originale", "public_path": "/news/titolo-originale"},
            {"route_version": 2, "category": "news-gaming", "title": "Titolo duplicato",
             "public_slug": "titolo-duplicato", "public_path": "/news/titolo-duplicato"},
        ]
        assign_public_routes(rows)
        self.assertEqual(rows[0]["public_path"], "/news/titolo-originale")
        self.assertEqual(rows[1]["public_path"], "/news/titolo-duplicato")

    def test_v2_route_must_be_persisted_before_build(self):
        with self.assertRaisesRegex(ValueError, "persisted public_path"):
            assign_public_routes([{"route_version": 2, "category": "guide", "title": "Guida al Wi-Fi"}])

if __name__ == "__main__":
    unittest.main()
