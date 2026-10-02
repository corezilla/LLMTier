"""MT-LOG-001 — OperationalLog 组装后脱敏与查询（M008 log，层①，security，P0）。

组装保证：record→落库 [REDACTED]、长度 ≤512、page 倒序/过滤/limit 夹取 200、
缺 since/until→400。经 M008 公开入口 record/page 驱动；ENV-1。
"""
from __future__ import annotations

import unittest

from http_api.errors import ApiError
from log.logs import OperationalLog
from tests.common.fakes import AppFixture


class LogAssemblyTests(unittest.TestCase):
    def setUp(self):
        self.fx = AppFixture()
        self.log = self.fx.app.logs

    def tearDown(self):
        self.fx.close()

    def test_record_then_page_roundtrip_redacts(self):
        self.log.record("info", "http", "request", "authorization: Bearer sk-123")
        page = self.log.page(since="2000-01-01T00:00:00Z", until="2100-01-01T00:00:00Z")
        self.assertEqual(1, len(page["data"]))
        row = page["data"][0]
        self.assertNotIn("sk-123", row["message"])
        self.assertIn("[REDACTED]", row["message"])

    def test_message_truncated_to_512(self):
        self.log.record("info", "http", "big", "x" * 2000)
        row = self.log.page(since="2000-01-01T00:00:00Z", until="2100-01-01T00:00:00Z")["data"][0]
        self.assertEqual(512, len(row["message"]))

    def test_desc_order_and_filters(self):
        for i in range(3):
            self.log.record("info", "http", "e", f"m{i}", f"req_{i}")
        self.log.record("warning", "admin", "e", "mw", "req_0")
        page = self.log.page(since="2000-01-01T00:00:00Z", until="2100-01-01T00:00:00Z")
        created = [r["created_at"] for r in page["data"]]
        self.assertEqual(created, sorted(created, reverse=True))
        only_warning = self.log.page(level="warning", since="2000-01-01T00:00:00Z", until="2100-01-01T00:00:00Z")
        self.assertEqual({"warning"}, {r["level"] for r in only_warning["data"]})
        by_request = self.log.page(request_id="req_1", since="2000-01-01T00:00:00Z", until="2100-01-01T00:00:00Z")
        self.assertEqual(1, len(by_request["data"]))

    def test_limit_clamped_to_200(self):
        for i in range(5):
            self.log.record("info", "http", "e", f"m{i}")
        page = self.log.page(limit=999, since="2000-01-01T00:00:00Z", until="2100-01-01T00:00:00Z")
        self.assertLessEqual(len(page["data"]), 200)
        page_low = self.log.page(limit=0, since="2000-01-01T00:00:00Z", until="2100-01-01T00:00:00Z")
        self.assertGreaterEqual(len(page_low["data"]), 1)

    def test_page_requires_since_and_until(self):
        with self.assertRaises(ApiError) as cm:
            self.log.page()
        self.assertEqual((400, "invalid_request"), (cm.exception.status, cm.exception.code))

    def test_newlines_flattened(self):
        self.log.record("info", "http", "e", "line1\nline2")
        row = self.log.page(since="2000-01-01T00:00:00Z", until="2100-01-01T00:00:00Z")["data"][0]
        self.assertNotIn("\n", row["message"])


if __name__ == "__main__":
    unittest.main()
