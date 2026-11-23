import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from community_youtube import (
    editorial_topic, merge_post_media, title_type,
    trim_youtube_promo_tail, webpage_json,
)
from review_pros_cons import attach, extract
import queue_collect


class YouTubeCommunityTitleTypeTests(unittest.TestCase):
    def test_all_editorial_families(self):
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

    def test_explicit_tech_and_gaming_prefixes_set_the_correct_topic(self):
        cases = {
            "NEWS TECH: Smartphone": "tech",
            "NEWS GAMING: Nuovo gioco": "gaming",
            "REVIEW TECH: Prodotto": "tech",
            "REVIEW GAMING: Videogioco": "gaming",
            "RECENSIONE/REVIEW TECH: Prodotto": "tech",
            "RECENSIONE/REVIEW GAMING: Videogioco": "gaming",
            "NEWS EXTRA: Evento": None,
            "NEWS SPECIALI: Analisi": None,
            "NEWS GUIDE: Configurazione": None,
        }
        for title, expected in cases.items():
            with self.subTest(title=title):
                self.assertEqual(editorial_topic(title), expected)

    def test_review_metadata_dependency_is_available_and_non_destructive(self):
        source = "PRO:\n- Buona qualità\nCONTRO:\n- Prezzo elevato"
        post = {"type": "review", "text": source}
        self.assertEqual(extract(source), {
            "pros": ["Buona qualità"], "cons": ["Prezzo elevato"]
        })
        self.assertIs(attach(post), post)
        self.assertEqual(post["text"], source)
        self.assertEqual(post["pros"], ["Buona qualità"])
        self.assertEqual(post["cons"], ["Prezzo elevato"])

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


class QueueCollectorClockTests(unittest.TestCase):
    def test_collection_is_allowed_at_every_time_of_day(self):
        from datetime import time as clock_time
        for value in ("00:00", "08:55", "12:20", "12:30", "15:55", "16:00", "19:25", "23:55"):
            with self.subTest(value=value):
                hour, minute = map(int, value.split(":"))
                self.assertTrue(queue_collect.in_intake_window(clock_time(hour, minute)))


if __name__ == "__main__":
    unittest.main()
