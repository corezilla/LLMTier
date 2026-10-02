"""MT-LOG-003 — page 分支 + 日志追加顺序（M008 log，层②/层④ T14，negative，P1）。

分支：缺 since/until→400、limit 夹取 [1,200]、level/module/request_id 过滤；
T14：append 顺序在 page 中倒序稳定（组装后经真实 Store）。
"""
from __future__ import annotations

import unittest

from http_api.errors import ApiError
from log.logs import OperationalLog
from tests.common.fakes import AppFixture


class PageBranchTests(unittest.TestCase):
    def setUp(self):
        self.fx = AppFixture()
        self.log = self.fx.app.logs
        for i in range(6):
            self.log.record("info" if i % 2 == 0 else "warning", "http" if i < 3 else "admin", "event", f"message-{i}", f"req_{i % 2}")

    def tearDown(self):
        self.fx.close()

    def _page(self, **kwargs):
        kwargs.setdefault("since", "2000-01-01T00:00:00Z")
        kwargs.setdefault("until", "2100-01-01T00:00:00Z")
        return self.log.page(**kwargs)

    def test_missing_since_or_until_is_400(self):
        for kwargs in ({}, {"since": "2000-01-01T00:00:00Z"}, {"until": "2100-01-01T00:00:00Z"}):
            with self.assertRaises(ApiError) as cm:
                self.log.page(**kwargs)
            self.assertEqual(400, cm.exception.status)

    def test_limit_clamped_low_and_high(self):
        self.assertEqual(1, len(self._page(limit=0)["data"]))
        self.assertEqual(1, len(self._page(limit=-5)["data"]))
        self.assertEqual(2, len(self._page(limit=2)["data"]))
        self.assertEqual(6, len(self._page(limit=999)["data"]))

    def test_filter_by_level_module_request_id(self):
        self.assertEqual(3, len(self._page(level="info")["data"]))
        self.assertEqual(3, len(self._page(module="http")["data"]))
        self.assertEqual(3, len(self._page(request_id="req_0")["data"]))
        combined = self._page(level="info", module="admin")
        self.assertEqual(1, len(combined["data"]))

    def test_append_order_is_stable_desc(self):
        first = [r["message"] for r in self._page()["data"]]
        self.assertEqual([f"message-{i}" for i in range(5, -1, -1)], first)
        self.assertEqual(first, [r["message"] for r in self._page()["data"]])


if __name__ == "__main__":
    unittest.main()
