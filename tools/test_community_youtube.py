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
        self.assertEqual(result["text"], full)
        self.assertIn("/post/" + POST_ID, mocked.call_args.args[0])

    def test_verified_result_keeps_longer_feed_text_and_marks_verification(self):
        feed = {"id": POST_ID, "text": "Testo dal feed più lungo " * 5}
        detail = {"id": POST_ID, "text": "Testo dettaglio"}
        with patch.object(importer, "fetch_post_detail", return_value=detail):
            result = importer.verify_post_details([feed])[0]
        self.assertEqual(result["text"], feed["text"])
        self.assertTrue(result["verified_detail"])
        self.assertTrue(result["text_complete"])
        self.assertEqual(result["text_source"], "youtube-post-detail")

    def test_unverified_batch_fails_closed(self):
        feed = {"id": POST_ID, "text": "NEWS TECH: testo dal feed"}
        with patch.object(importer, "fetch_post_detail", side_effect=RuntimeError("detail unavailable")):
            with self.assertRaisesRegex(RuntimeError, "no unverified batch imported"):
                importer.verify_post_details([feed])

    def test_rich_text_runs_preserve_all_segments(self):
        rich = {"runs": [{"text": "Prima parte. "}, {"text": "Seconda parte."}]}
        self.assertEqual(importer.value(rich), "Prima parte. Seconda parte.")


if __name__ == "__main__":
    unittest.main()
