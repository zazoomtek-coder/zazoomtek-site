import unittest
from unittest.mock import patch

import scheduled_editorial_import as importer


class CommunityQueueVerificationTests(unittest.TestCase):
    def test_legacy_queue_records_are_reverified_before_import(self):
        old = {"id": "Ugabcdefghijklm", "text": "Short excerpt"}
        full = {
            **old,
            "text": "Complete verified Community post with all paragraphs.",
            "verified_detail": True,
            "text_complete": True,
        }
        with patch.object(importer, "verify_post_details", return_value=[full]) as mocked:
            result = importer.verify_community_queue_rows([old], set(), set())
        mocked.assert_called_once_with([old])
        self.assertEqual(result, [full])

    def test_already_published_or_archived_ids_are_not_refetched(self):
        old = {"id": "Ugabcdefghijklm", "text": "Old queue excerpt"}
        with patch.object(importer, "verify_post_details") as mocked:
            result = importer.verify_community_queue_rows(
                [old], {"Ugabcdefghijklm"}, set()
            )
        self.assertEqual(result, [])
        mocked.assert_not_called()

        with patch.object(importer, "verify_post_details") as mocked:
            result = importer.verify_community_queue_rows(
                [old], set(), {"Ugabcdefghijklm"}
            )
        self.assertEqual(result, [])
        mocked.assert_not_called()

    def test_verified_full_queue_records_do_not_need_another_fetch(self):
        full = {
            "id": "Ugabcdefghijklm",
            "text": "Complete text",
            "verified_detail": True,
            "text_complete": True,
        }
        with patch.object(importer, "verify_post_details") as mocked:
            result = importer.verify_community_queue_rows([full], set(), set())
        self.assertEqual(result, [full])
        mocked.assert_not_called()

    def test_unavailable_detail_fails_closed(self):
        old = {"id": "Ugabcdefghijklm", "text": "Unverified excerpt"}
        with patch.object(importer, "verify_post_details", side_effect=RuntimeError("offline")):
            result = importer.verify_community_queue_rows([old], set(), set())
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
