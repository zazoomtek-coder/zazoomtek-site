import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from community_youtube import merge_post_media, title_type, trim_youtube_promo_tail, webpage_json
from build import category_for_post


class YouTubeCommunityTitleTypeTests(unittest.TestCase):
    def test_all_six_editorial_families(self):
        cases = {
            "NEWS TECH: Smartphone": "news",
            "NEWS GAMING: Nuovo gioco": "news",
            "NEWS EXTRA: Speciale evento": "extra",
            "NEWS SPECIALI: Analisi": "speciali",
            "NEWS GUIDE: Configurazione": "guide",
            "NEWS GUIDES: Impostazioni": "guide",
            "RECENSIONE: Prodotto": "review",
            "RECENSIONE TECH: Prodotto": "review",
            "RECENSIONE GAMING: Gioco": "review",
            "REVIEW: Prodotto": "review",
            "REVIEW TECH: Prodotto": "review",
            "REVIEW GAMING: Gioco": "review",
            "RECENSIONE/REVIEW: Prodotto": "review",
        }
        for title, expected in cases.items():
            with self.subTest(title=title):
                parsed_title, kind = title_type(title)
                self.assertEqual(parsed_title, title)
                self.assertEqual(kind, expected)

    def test_all_six_prefix_families_route_to_public_site_categories(self):
        cases = {
            "NEWS TECH: Smartphone": "news-tech",
            "NEWS GAMING: Nuovo gioco": "news-gaming",
            "NEWS EXTRA: Evento": "extra",
            "NEWS SPECIALI: Analisi": "speciali",
            "NEWS GUIDE: Configurazione": "guide",
            "REVIEW TECH: Prodotto": "recensioni-tech",
            "REVIEW GAMING: Videogioco": "recensioni-gaming",
            "RECENSIONE/REVIEW: Prodotto": "recensioni-tech",
        }
        for title, expected in cases.items():
            with self.subTest(title=title):
                self.assertEqual(category_for_post({
                    "title": title, "type": "news", "topic": "tech",
                    "text_complete": True
                }), expected)

    def test_detail_page_without_attachment_preserves_feed_cover_and_extra_images(self):
        listing = {
            "image": "https://yt3.ggpht.com/feed-cover=s1600",
            "images": [{"src": "https://yt3.ggpht.com/feed-extra=s1600", "caption": "Extra"}],
        }
        detail = {"id": "UgExample123456", "text": "Testo completo", "image": "", "images": []}
        merged = merge_post_media(listing, detail)
        self.assertEqual(merged["image"], listing["image"])
        self.assertEqual(merged["images"], listing["images"])
        self.assertEqual(merged["text"], "Testo completo")

    def test_detail_page_media_is_merged_without_dropping_feed_media(self):
        listing = {
            "image": "https://yt3.ggpht.com/feed-cover=s1600",
            "images": [{"src": "https://yt3.ggpht.com/feed-extra=s1600", "caption": ""}],
        }
        detail = {
            "image": "https://yt3.ggpht.com/detail-cover=s1600",
            "images": [{"src": "https://yt3.ggpht.com/detail-extra=s1600", "caption": ""}],
        }
        merged = merge_post_media(listing, detail)
        self.assertEqual(merged["image"], listing["image"])
        self.assertEqual(
            [item["src"] for item in merged["images"]],
            [detail["image"], listing["images"][0]["src"], detail["images"][0]["src"]],
        )

    def test_detail_page_cover_is_used_when_feed_has_no_cover(self):
        detail = {"image": "https://yt3.ggpht.com/detail-cover=s1600", "images": []}
        merged = merge_post_media({"image": "", "images": []}, detail)
        self.assertEqual(merged["image"], detail["image"])

    def test_webpage_json_reads_script_assignment_and_embedded_key(self):
        assignment = '<script>var ytInitialData = {"contents":{"ok":true}};</script>'
        embedded = '<script>{"ytInitialData":{"contents":{"value":2}}}</script>'
        self.assertEqual(webpage_json(assignment), {"contents": {"ok": True}})
        self.assertEqual(webpage_json(embedded), {"contents": {"value": 2}})

    def test_community_text_stops_at_required_cta(self):
        source = ("Testo editoriale.\\nSe ti piacciono tecnologia, gaming, unboxing e recensioni, "
                  "segui ZazoomTek.\\nSubscribe, social, hashtag e link")
        self.assertEqual(
            trim_youtube_promo_tail(source),
            "Testo editoriale.\\nSe ti piacciono tecnologia, gaming, unboxing e recensioni, segui ZazoomTek."
        )

    def test_legacy_prefixes_remain_supported(self):
        cases = {
            "Guida: Wi-Fi": "guide",
            "Speciale: Gaming": "speciali",
            "Extra: Evento": "extra",
            "News: Aggiornamento": "news",
        }
        for title, expected in cases.items():
            with self.subTest(title=title):
                self.assertEqual(title_type(title)[1], expected)


if __name__ == "__main__":
    unittest.main()
