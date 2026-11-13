import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from editorial_scope import imported_ids, is_release_critical, record_issue


class EditorialScopeTests(unittest.TestCase):
    def test_v2_is_always_release_critical(self):
        self.assertTrue(is_release_critical({"route_version": 2, "id": "old-v2"}))

    def test_historical_legacy_record_is_non_blocking(self):
        self.assertFalse(is_release_critical({"legacy_path": "/community-old", "id": "old"}))

    def test_newly_imported_legacy_record_is_critical_by_manifest(self):
        self.assertTrue(is_release_critical({"id": "fresh"}, {"fresh"}))

    def test_manifest_is_read_safely(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, ".editorial-import-manifest.json").write_text(
                '{"strict_ids":["fresh","fresh-video"]}', encoding="utf-8")
            self.assertEqual(imported_ids(tmp), {"fresh", "fresh-video"})

    def test_malformed_manifest_fails_open_without_hiding_v2(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, ".editorial-import-manifest.json").write_text("{broken", encoding="utf-8")
            self.assertEqual(imported_ids(tmp), set())
            self.assertTrue(is_release_critical({"route_version": "v2"}))

    def test_issue_severity_is_explicit(self):
        errors, warnings = [], []
        record_issue(errors, warnings, "historic issue", False)
        record_issue(errors, warnings, "new issue", True)
        self.assertEqual(errors, ["new issue"])
        self.assertEqual(warnings, ["historic issue"])


if __name__ == "__main__":
    unittest.main()
