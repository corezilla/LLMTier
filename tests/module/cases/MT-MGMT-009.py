"""MT-MGMT-009 — usage 分页 cursor 四态（M004，层②/层③ K3，boundary，P0）。

K3 组合行：(无 cursor, 首页)/(有效 cursor, 下一页)/(过期 cursor, 400)/
(有效 cursor, 超出总分页, 空页)；跨 principal→403、过滤不符→400；旧页冻结。
"""
from __future__ import annotations

import unittest

from http_api.errors import ApiError
from tests.common.fakes import FakeAdapter
from tests.module.cases.support.inference_env import RESPONSE_BODY, InferenceEnv


class UsageCursorTests(InferenceEnv):
    def _make_records(self, count, principal="consumer"):
        self.fx.app.responses._test_adapter = FakeAdapter(usage=True)
        try:
            for i in range(count):
                self.fx.app.responses.create(principal, f"req_cursor_{principal}_{i}", RESPONSE_BODY)
        finally:
            self.fx.app.responses._test_adapter = None

    def _page(self, principal="consumer", cursor=None, limit=2, admin=False, since="2000-01-01T00:00:00Z", until="2100-01-01T00:00:00Z", model=None, request_id=None):
        return self.fx.app.usage.page(principal, cursor, limit, admin=admin, since=since, until=until, model=model, request_id=request_id)

    def test_first_page_then_next_page(self):
        self._make_records(3)
        page1 = self._page()
        self.assertEqual(2, len(page1["data"]))
        self.assertTrue(page1["has_more"])
        page2 = self._page(cursor=page1["next_cursor"])
        self.assertEqual(1, len(page2["data"]))
        ids1 = {r["request_id"] for r in page1["data"]}
        ids2 = {r["request_id"] for r in page2["data"]}
        self.assertFalse(ids1 & ids2)

    def test_expired_cursor_is_400(self):
        self._make_records(1)
        with self.assertRaises(ApiError) as cm:
            self._page(cursor="snap_missing:0")
        self.assertEqual(("cursor_expired", 400), (cm.exception.code, cm.exception.status))

    def test_cross_principal_cursor_is_403(self):
        self._make_records(1)
        page = self._page(principal="alice")
        with self.assertRaises(ApiError) as cm:
            self._page(principal="mallory", cursor=page["next_cursor"] or f"{page['snapshot_id']}:0")
        self.assertEqual(("permission_denied", 403), (cm.exception.code, cm.exception.status))

    def test_filter_mismatch_is_400(self):
        self._make_records(3)
        page = self._page(model=None)
        with self.assertRaises(ApiError) as cm:
            self._page(cursor=page["next_cursor"] or f"{page['snapshot_id']}:0", model="Other")
        self.assertEqual(("invalid_request", 400), (cm.exception.code, cm.exception.status))

    def test_beyond_total_is_empty_page(self):
        self._make_records(2)
        page1 = self._page(limit=2)
        self.assertFalse(page1["has_more"])
        self.assertIsNone(page1["next_cursor"])
        page_far = self._page(cursor=f"{page1['snapshot_id']}:50")
        self.assertEqual([], page_far["data"])
        self.assertIsNone(page_far["next_cursor"])

    def test_old_page_frozen_against_new_records(self):
        self._make_records(2)
        page1 = self._page(limit=10)
        frozen_ids = [r["request_id"] for r in page1["data"]]
        self._make_records(1, principal="consumer2")
        page_again = self._page(limit=10)
        self.assertEqual(frozen_ids, [r["request_id"] for r in page_again["data"]])


if __name__ == "__main__":
    unittest.main()
