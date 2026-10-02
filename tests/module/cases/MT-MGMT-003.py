"""MT-MGMT-003 — 分页快照与清空计数（M004，层①，boundary，P0）。

组装保证：admin.page 首屏后新数据不进旧页（游标冻结）；范围清空计数一致；
垃圾/过期 cursor→400 `cursor_expired`。
"""
from __future__ import annotations

import unittest

from tests.module.cases.support.http_env import LoopbackEnv


class PaginationFreezeTests(LoopbackEnv):
    def _create_provider(self, name):
        status, payload, _ = self.request("POST", "/v1/providers",
                                          body={"name": name, "kind": "local", "endpoint": "http://127.0.0.1:9",
                                                "secret_ref": None, "enabled": True})
        self.assertEqual(201, status)

    def test_first_page_frozen_against_later_writes(self):
        for i in range(3):
            self._create_provider(f"frozen-{i}")
        status, page1, _ = self.request("GET", "/v1/providers?limit=2")
        self.assertEqual(2, len(page1["data"]))
        self.assertTrue(page1["page"]["has_more"])
        cursor = page1["page"]["next_cursor"]
        page1_ids = {p["id"] for p in page1["data"]}
        # 快照建立后再写：旧页冻结（第二页不含新资源）
        self._create_provider("frozen-late")
        status, page2, _ = self.request("GET", f"/v1/providers?limit=2&cursor={cursor}")
        page2_names = {p["name"] for p in page2["data"]}
        self.assertNotIn("frozen-late", page2_names)
        self.assertFalse({p["id"] for p in page2["data"]} & page1_ids)
        # 首屏内容不因后续写入而变化
        status, page1_again, _ = self.request("GET", f"/v1/providers?limit=2&cursor={cursor}")
        self.assertEqual([p["id"] for p in page2["data"]], [p["id"] for p in page1_again["data"]])

    def test_garbage_cursor_is_400(self):
        status, payload, _ = self.request("GET", "/v1/providers?cursor=not-a-cursor")
        self.assertEqual(400, status)
        self.assertEqual("cursor_expired", payload["error"]["code"])

    def test_unknown_snapshot_cursor_is_400(self):
        status, payload, _ = self.request("GET", "/v1/providers?cursor=admin_missing:0")
        self.assertEqual(400, status)
        self.assertEqual("cursor_expired", payload["error"]["code"])


class ResetUsageTests(LoopbackEnv):
    def _seed_usage(self, count=2):
        from tests.common.fakes import FakeAdapter
        self.fx.app.responses._test_adapter = FakeAdapter(usage=True)
        try:
            for i in range(count):
                self.fx.app.responses.create("consumer", f"req_reset_{i}",
                                             {"model": "Worker", "input": "hi", "stream": True, "store": False})
        finally:
            self.fx.app.responses._test_adapter = None

    def test_scoped_reset_count_matches(self):
        self._seed_usage(2)
        status, page, _ = self.request("GET", "/v1/usage?from=2000-01-01T00:00:00Z&to=2100-01-01T00:00:00Z")
        before = len(page["data"])
        self.assertEqual(2, before)
        status, result, _ = self.request("DELETE", "/v1/usage?from=2000-01-01T00:00:00Z&to=2100-01-01T00:00:00Z")
        self.assertEqual(200, status)
        # 每请求写 head + 2 个版本行（unknown@authorize + measured@finish），
        # 计数按 version 行（4），页面按 head（2）——清空后两侧归零
        self.assertEqual(2 * before, result["deleted"])
        status, page2, _ = self.request("GET", "/v1/usage?from=2000-01-01T00:00:00Z&to=2100-01-01T00:00:00Z")
        self.assertEqual(0, len(page2["data"]))


if __name__ == "__main__":
    unittest.main()
