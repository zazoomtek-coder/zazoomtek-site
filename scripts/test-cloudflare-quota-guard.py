#!/usr/bin/env python3
"""Regression tests for editorial-first throttling. Runs off-site in CI."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone

file = Path(__file__).with_name("cloudflare-quota-guard.py")
spec = importlib.util.spec_from_file_location("cf_quota_guard", file)
quota = importlib.util.module_from_spec(spec)
spec.loader.exec_module(quota)

class QuotaTests(unittest.TestCase):
    def test_editorial_halts_first(self):
        self.assertTrue(quota.permitted("editorial", 349))
        self.assertFalse(quota.permitted("editorial", 350))
        self.assertTrue(quota.permitted("featured", 350))
        self.assertTrue(quota.permitted("news", 350))

    def test_featured_halts_before_news(self):
        self.assertTrue(quota.permitted("featured", 399))
        self.assertFalse(quota.permitted("featured", 400))
        self.assertTrue(quota.permitted("news", 400))

    def test_news_then_urgent_halt(self):
        self.assertTrue(quota.permitted("news", 484))
        self.assertFalse(quota.permitted("news", 485))
        self.assertTrue(quota.permitted("urgent", 485))
        self.assertFalse(quota.permitted("urgent", 495))
        self.assertFalse(quota.permitted("urgent", 500))

    def test_unknown_source_fails_closed(self):
        with self.assertRaises(quota.QuotaError):
            quota.permitted("unknown", 200)
        with self.assertRaises(quota.QuotaError):
            quota.permitted("news", -1)

    def test_timestamp_requires_timezone(self):
        self.assertEqual(quota.parse_date("2026-10-15T12:00:00Z").tzinfo, timezone.utc)
        with self.assertRaises(quota.QuotaError):
            quota.parse_date("2026-10-15T12:00:00")

    def test_counts_all_projects_previews_and_failures(self):
        recent = datetime.now(timezone.utc).isoformat()
        old = (datetime.now(timezone.utc) - timedelta(days=35)).isoformat()
        def fake_paged(path):
            if path.endswith("/pages/projects"):
                return iter([{"name":"a"},{"name":"b"}])
            if path.endswith("/a/deployments"):
                return iter([
                    {"id":"1","created_on":recent},
                    {"id":"1","created_on":recent},
                    {"id":"2","created_on":recent,"skip_reason":"commit_message"},
                    {"id":"3","created_on":old}
                ])
            if path.endswith("/b/deployments"):
                return iter([{"id":"4","created_on":recent, "deployment_trigger":{"type":"push"}}])
            raise AssertionError(path)
        with patch.dict(quota.os.environ,{"CLOUDFLARE_ACCOUNT_ID":"abcdef123"}):
            with patch.object(quota,"paged",side_effect=fake_paged):
                self.assertEqual(quota.count_recent_attempts(), 2)

if __name__ == "__main__":
    unittest.main()
