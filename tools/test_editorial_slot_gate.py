import os
import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import editorial_slot_gate as gate


class CollectionOnlyPollingGateTests(unittest.TestCase):
    def test_poll_can_never_authorize_a_public_release(self):
        now = datetime(2026, 11, 23, 16, 37, 48, tzinfo=ZoneInfo("Europe/Rome"))
        with patch.dict(os.environ, {
            "EDITORIAL_REQUESTED_SLOT": "poll",
            "EDITORIAL_FORCE_RELEASE": "false",
        }, clear=False):
            target = gate.requested_slot(now)
        self.assertIsNone(target)

    def test_legacy_daily_slots_remain_supported(self):
        now = datetime(2026, 11, 23, 16, 1, 0, tzinfo=ZoneInfo("Europe/Rome"))
        with patch.dict(os.environ, {
            "EDITORIAL_REQUESTED_SLOT": "16:00",
            "EDITORIAL_FORCE_RELEASE": "false",
            "EDITORIAL_SLOT_GATE_PASSED": "true",
        }, clear=False):
            target = gate.requested_slot(now)
        self.assertEqual(target, datetime(2026, 11, 23, 16, 0, tzinfo=ZoneInfo("Europe/Rome")))


if __name__ == "__main__":
    unittest.main()
