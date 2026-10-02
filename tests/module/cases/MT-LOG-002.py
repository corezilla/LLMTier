"""MT-LOG-002 — 脱敏五模式 × 位置（M008 log，层②/层③ K10，security，P0）。

K10 组合行：Bearer 行首/token= 行中/api_key 行尾/authorization 键值/普通文本不误伤。
组装保证：五种敏感模式经真实落库后读回均为 [REDACTED]。
"""
from __future__ import annotations

import unittest

from log.logs import OperationalLog
from tests.common.fakes import AppFixture


class RedactionMatrixTests(unittest.TestCase):
    def setUp(self):
        self.fx = AppFixture()
        self.log = self.fx.app.logs

    def tearDown(self):
        self.fx.close()

    def _message(self, text):
        self.log.record("info", "http", "e", text)
        return self.log.page(since="2000-01-01T00:00:00Z", until="2100-01-01T00:00:00Z")["data"][0]["message"]

    def test_bearer_at_start(self):
        message = self._message("Bearer abc123 trailing")
        self.assertNotIn("abc123", message)
        self.assertIn("[REDACTED]", message)

    def test_token_mid_line(self):
        message = self._message("prefix token=abc123 suffix")
        self.assertNotIn("abc123", message)
        self.assertIn("[REDACTED]", message)

    def test_api_key_at_end(self):
        message = self._message("prefix api_key:XYZ999")
        self.assertNotIn("XYZ999", message)
        self.assertIn("[REDACTED]", message)

    def test_authorization_header_style(self):
        message = self._message("Authorization: Bearer q-token-1")
        self.assertNotIn("q-token-1", message)
        self.assertIn("[REDACTED]", message)

    def test_secret_and_access_key(self):
        self.assertNotIn("s3cr3t", self._message("secret=s3cr3t"))
        self.assertNotIn("AKIA01", self._message("access_key_id=AKIA01"))

    def test_plain_text_not_redacted(self):
        self.assertEqual("token bucket limiter and keyboard", self._message("token bucket limiter and keyboard"))
        self.assertEqual("see apikeys folder", self._message("see apikeys folder"))

    def test_case_insensitive_hit(self):
        message = self._message("API_KEY=upper")
        self.assertNotIn("upper", message)


if __name__ == "__main__":
    unittest.main()
