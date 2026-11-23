import json
import unittest
from unittest.mock import patch

import community_youtube as importer


POST_ID = "Ugabcdefghijklm"


def page(text):
    payload = {
        "contents": {
            "postRenderer": {
                "postId": POST_ID,
                "contentText": {"runs": [{"text": text}]},
                "publishedTimeText": {"simpleText": "oggi"},
            }
        }
    }
    return "<script>var ytInitialData = " + json.dumps(payload, ensure_ascii=False) + ";</script>"


class CommunityFullTextTests(unittest.TestCase):
    def test_renderer_prefers_longest_expanded_text_field(self):
        short = "NEWS TECH: Google Maps integra Trenord..."
        full = short[:-3] + " in tempo reale, con orari, ritardi e coincidenze."
        root = {
            "postRenderer": {
                "postId": POST_ID,
                "contentText": {"runs": [{"text": short}]},
                "expandedText": {"runs": [{"text": full}]},
            }
        }
        self.assertEqual(importer.post_records(root)[0]["text"], full)

    def test_detail_page_is_read_and_decoded(self):
        full = "NEWS TECH: " + ("Testo integrale del post. " * 12)
        with patch.object(importer, "fetch", return_value=page(full)) as mocked:
            result = importer.fetch_post_detail(POST_ID, attempts=1)
        self.assertEqual(result["text"], full.strip())
        self.assertIn("/post/" + POST_ID, mocked.call_args.args[0])

    def test_shorter_detail_is_not_imported_and_can_be_retried(self):
        feed = {"id": POST_ID, "text": "Testo dal feed più lungo " * 5}
        detail = {"id": POST_ID, "text": "Testo dettaglio"}
        with patch.object(importer, "fetch_post_detail", return_value=detail):
            result = importer.verify_post_details([feed])
        self.assertEqual(result, [])

    def test_detail_with_trailing_ellipsis_is_not_complete(self):
        text = "NEWS TECH: testo ancora abbreviato..."
        feed = {"id": POST_ID, "text": text}
        with patch.object(importer, "fetch_post_detail", return_value={"id": POST_ID, "text": text}):
            result = importer.verify_post_details([feed])[0]
        self.assertEqual(result, [])

    def test_full_detail_page_confirms_complete_text(self):
        text = "NEWS TECH: " + ("Testo integrale completo. " * 8)
        feed = {"id": POST_ID, "text": text}
        with patch.object(importer, "fetch_post_detail", return_value={"id": POST_ID, "text": text}):
            result = importer.verify_post_details([feed])[0]
        self.assertTrue(result["text_complete"])

    def test_all_unverified_posts_are_retried(self):
        feed = {"id": POST_ID, "text": "NEWS TECH: testo dal feed"}
        with patch.object(importer, "fetch_post_detail", side_effect=RuntimeError("detail unavailable")):
            with self.assertRaisesRegex(RuntimeError, "No individual YouTube Community post could be verified"):
                importer.verify_post_details([feed])

    def test_one_failed_detail_does_not_block_other_complete_posts(self):
        second_id = "Ugmnopqrstuvwxyz"
        first = {"id": POST_ID, "text": "NEWS TECH: testo completo " * 4}
        second = {"id": second_id, "text": "NEWS TECH: testo da verificare"}
        full_detail = {"id": POST_ID, "text": first["text"]}
        def detail(post_id):
            if post_id == POST_ID:
                return full_detail
            raise RuntimeError("temporary detail failure")
        with patch.object(importer, "fetch_post_detail", side_effect=detail):
            result = importer.verify_post_details([first, second])
        self.assertEqual([row["id"] for row in result], [POST_ID])

    def test_rich_text_runs_preserve_all_segments(self):
        rich = {"runs": [{"text": "Prima parte. "}, {"text": "Seconda parte."}]}
        self.assertEqual(importer.value(rich), "Prima parte. Seconda parte.")


    def test_feed_images_survive_detail_page_without_media(self):
        listing = {
            "id": POST_ID,
            "image": "https://yt3.ggpht.com/feed-cover=s1600",
            "images": [{"src": "https://yt3.ggpht.com/feed-extra=s1600", "caption": ""}],
        }
        detail = {"id": POST_ID, "text": "Testo completo", "image": "", "images": []}
        merged = importer.merge_post_media(listing, detail)
        self.assertEqual(merged["image"], listing["image"])
        self.assertEqual(merged["images"], listing["images"])
        self.assertEqual(merged["text"], "Testo completo")

    def test_detail_media_is_added_without_replacing_feed_cover(self):
        listing = {
            "image": "https://yt3.ggpht.com/feed-cover=s1600",
            "images": [{"src": "https://yt3.ggpht.com/feed-extra=s1600", "caption": ""}],
        }
        detail = {
            "image": "https://yt3.ggpht.com/detail-cover=s1600",
            "images": [{"src": "https://yt3.ggpht.com/detail-extra=s1600", "caption": ""}],
        }
        merged = importer.merge_post_media(listing, detail)
        self.assertEqual(merged["image"], listing["image"])
        self.assertEqual(
            [item["src"] for item in merged["images"]],
            [detail["image"], listing["images"][0]["src"], detail["images"][0]["src"]],
        )

    def test_editorial_topic_and_legacy_heading_compatibility(self):
        self.assertEqual(importer.editorial_topic("NEWS TECH: Smartphone"), "tech")
        self.assertEqual(importer.editorial_topic("NEWS GAMING: Videogioco"), "gaming")
        self.assertIsNone(importer.editorial_topic("NEWS GUIDE: Configurazione"))
        self.assertEqual(importer.title_type("NEWS GUIDES: Impostazioni")[1], "guide")
        self.assertEqual(importer.title_type("RECENSIONE/REVIEW: Prodotto")[1], "review")

    def test_promotional_tail_is_removed_after_cta(self):
        source = ("Testo editoriale.\\nSe ti piacciono tecnologia, gaming, unboxing e recensioni, "
                  "segui ZazoomTek.\\nSubscribe, social, hashtag e link")
        expected = ("Testo editoriale.\\nSe ti piacciono tecnologia, gaming, unboxing e recensioni, "
                    "segui ZazoomTek.")
        self.assertEqual(importer.trim_youtube_promo_tail(source), expected)


if __name__ == "__main__":
    unittest.main()
