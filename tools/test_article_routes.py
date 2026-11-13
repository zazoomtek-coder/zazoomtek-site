import unittest
from tools.article_routes import build_article_url, normalize_public_path, slugify_title, unique_slug

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
                "slug": expected.rsplit("/", 1)[-1],
            }), expected)

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
        self.assertEqual(unique_slug("Nuovo smartphone", occupied), "nuovo-smartphone")
        self.assertEqual(unique_slug("Nuovo smartphone", occupied), "nuovo-smartphone-2")

if __name__ == "__main__":
    unittest.main()
