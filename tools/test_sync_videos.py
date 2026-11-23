import json
import unittest
from unittest.mock import patch

import sync_videos as importer


def page(payload):
    return '<script>var ytInitialData = ' + json.dumps(payload, ensure_ascii=False) + ';</script>'


class YouTubeUploadPaginationTests(unittest.TestCase):
    def test_reads_standard_video_renderers_and_ignores_shorts(self):
        payload = {
            "contents": {
                "videoRenderer": {
                    "videoId": "abcdefghijk",
                    "title": {"runs": [{"text": "Recensione smartphone"}]},
                    "publishedTimeText": {"simpleText": "2 days ago"},
                },
                "shorts": {
                    "reelItemRenderer": {
                        "videoId": "lmnopqrstuv",
                        "headline": {"simpleText": "Short"},
                    }
                },
            }
        }
        with patch.object(importer, "_fetch_channel_page", return_value=page(payload)):
            rows = importer.discover_uploads(limit=20, max_pages=2)
        self.assertEqual([row["id"] for row in rows], ["abcdefghijk"])
        self.assertEqual(rows[0]["published_label"], "2 days ago")

    def test_follows_continuation_pages(self):
        first = {
            "contents": {
                "videoRenderer": {
                    "videoId": "abcdefghijk",
                    "title": {"simpleText": "First upload"},
                    "publishedTimeText": {"simpleText": "1 day ago"},
                },
                "continuationItemRenderer": {
                    "continuationEndpoint": {
                        "continuationCommand": {"token": "NEXT_PAGE"}
                    }
                },
            }
        }
        second = {
            "onResponseReceivedActions": [{
                "appendContinuationItemsAction": {
                    "continuationItems": [{
                        "gridVideoRenderer": {
                            "videoId": "lmnopqrstuv",
                            "title": {"simpleText": "Second upload"},
                            "publishedTimeText": {"simpleText": "2 days ago"},
                        }
                    }]
                }
            }]
        }
        html = page(first) + '<script>{"INNERTUBE_API_KEY":"test-key","INNERTUBE_CLIENT_VERSION":"test-version"}</script>'
        with patch.object(importer, "_fetch_channel_page", side_effect=[html, json.dumps(second)]) as mocked:
            rows = importer.discover_uploads(limit=20, max_pages=3)
        self.assertEqual({row["id"] for row in rows}, {"abcdefghijk", "lmnopqrstuv"})
        self.assertEqual(mocked.call_count, 2)

    def test_tries_alternate_channel_endpoint_when_first_is_blocked(self):
        payload = {
            "contents": {
                "videoRenderer": {
                    "videoId": "abcdefghijk",
                    "title": {"simpleText": "First upload"},
                    "publishedTimeText": {"simpleText": "1 day ago"},
                }
            }
        }
        with patch.object(importer, "_fetch_channel_page",
                          side_effect=["<html>blocked</html>", page(payload)]) as mocked:
            rows = importer.discover_uploads(limit=20, max_pages=1)
        self.assertEqual([row["id"] for row in rows], ["abcdefghijk"])
        self.assertEqual(mocked.call_count, 2)

    def test_empty_channel_payload_fails_closed(self):
        with patch.object(importer, "_fetch_channel_page", return_value="<html>unavailable</html>"):
            with self.assertRaisesRegex(ValueError, "no ytInitialData"):
                importer.discover_uploads()


    def test_skips_initial_data_shell_and_tries_next_channel_endpoint(self):
        shell = {"contents": {"twoColumnBrowseResultsRenderer": {"tabs": []}}}
        payload = {
            "contents": {
                "videoRenderer": {
                    "videoId": "abcdefghijk",
                    "title": {"simpleText": "First upload"},
                    "publishedTimeText": {"simpleText": "1 day ago"},
                }
            }
        }
        with patch.object(importer, "_fetch_channel_page",
                          side_effect=[page(shell), page(payload)]) as mocked:
            rows = importer.discover_uploads(limit=20, max_pages=1)
        self.assertEqual([row["id"] for row in rows], ["abcdefghijk"])
        self.assertEqual(mocked.call_count, 2)



    def test_uses_innertube_videos_tab_when_channel_html_has_only_shells(self):
        shell = {"contents": {"twoColumnBrowseResultsRenderer": {"tabs": []}}}
        payload = {
            "contents": {
                "videoRenderer": {
                    "videoId": "abcdefghijk",
                    "title": {"simpleText": "Innertube upload"},
                    "publishedTimeText": {"simpleText": "1 day ago"},
                }
            }
        }
        html = page(shell) + '<script>{"INNERTUBE_API_KEY":"test-key","INNERTUBE_CLIENT_VERSION":"test-version"}</script>'
        with patch.object(importer, "_fetch_channel_page",
                          side_effect=[html, html, html, html, html, json.dumps(payload)]) as mocked:
            rows = importer.discover_uploads(limit=20, max_pages=1)
        self.assertEqual([row["id"] for row in rows], ["abcdefghijk"])
        self.assertEqual(mocked.call_count, 6)
        browse_url, request_body = mocked.call_args.args[:2]
        self.assertIn("key=test-key", browse_url)
        request = json.loads(request_body)
        self.assertEqual(request["browseId"], importer.CHANNEL_ID)
        self.assertEqual(request["params"], "EgZ2aWRlb3PyBgQKAjoA")
        self.assertEqual(request["context"]["client"]["clientVersion"], "test-version")



if __name__ == "__main__":
    unittest.main()
