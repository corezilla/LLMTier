"""MT-DIAG-006 — 游标与时间窗分支（M006，层②/层③ K9，boundary，P1）。

K9 组合行：(traces, 非法)/(traces, 时间窗越界)/(snapshots, 非法)/
(snapshots, 分页 next)；`next_cursor`/`has_more` 稳定，时间窗越界为空。
"""
from __future__ import annotations

import unittest

from tests.module.cases.support.inference_env import InferenceEnv


class CursorTests(InferenceEnv):
    def _seed(self, count, with_snapshots=True):
        self.fx.app.diagnostics.set_switches(snapshots_enabled=with_snapshots, stats_enabled=False)
        for i in range(count):
            self.fx.app.diagnostics.record_trace(f"req_cursor_{i}", "received", {"i": i}, correlation_id=None)
        if with_snapshots:
            for i in range(count):
                self.fx.app.diagnostics.capture_snapshot(f"req_cursor_{i}", self.senior["id"], "Senior",
                                                          "http://127.0.0.1:1/v1", "backend", 200, 1.0, None)

    def test_traces_invalid_cursor_is_400(self):
        self._seed(2)
        with self.assertRaises(Exception) as cm:
            self.fx.app.diagnostics.traces("2000-01-01T00:00:00Z", "2100-01-01T00:00:00Z", cursor="no-separator")
        self.assertEqual(("cursor_expired", 400), (cm.exception.code, cm.exception.status))

    def test_traces_beyond_window_is_empty(self):
        self._seed(1)
        self.assertEqual([], self.fx.app.diagnostics.traces("2000-01-01T00:00:00Z", "2000-01-02T00:00:00Z")["items"])

    def test_snapshots_invalid_cursor_is_400(self):
        self._seed(1)
        with self.assertRaises(Exception) as cm:
            self.fx.app.diagnostics.snapshots_page("2000-01-01T00:00:00Z", "2100-01-01T00:00:00Z", None, None, cursor="snap_missing")
        self.assertEqual(("cursor_expired", 400), (cm.exception.code, cm.exception.status))

    def test_snapshots_paging_is_stable(self):
        self._seed(3)
        page1 = self.fx.app.diagnostics.snapshots_page("2000-01-01T00:00:00Z", "2100-01-01T00:00:00Z", None, None, limit=2)
        self.assertEqual(2, len(page1["items"]))
        self.assertTrue(page1["has_more"])
        self.assertIsNotNone(page1["next_cursor"])
        page2 = self.fx.app.diagnostics.snapshots_page("2000-01-01T00:00:00Z", "2100-01-01T00:00:00Z", None, None,
                                                       limit=2, cursor=page1["next_cursor"])
        self.assertEqual(1, len(page2["items"]))
        self.assertFalse(page2["has_more"])
        self.assertIsNone(page2["next_cursor"])
        ids1 = {i["id"] for i in page1["items"]}
        ids2 = {i["id"] for i in page2["items"]}
        self.assertFalse(ids1 & ids2)

    def test_limit_clamped_on_both_faces(self):
        self._seed(2)
        # limit 夹取到 [1,500]：0/-1 → 1，超大 → 全部
        self.assertEqual(1, len(self.fx.app.diagnostics.snapshots_page("2000-01-01T00:00:00Z", "2100-01-01T00:00:00Z", None, None, limit=0)["items"]))
        self.assertEqual(1, len(self.fx.app.diagnostics.snapshots_page("2000-01-01T00:00:00Z", "2100-01-01T00:00:00Z", None, None, limit=-3)["items"]))
        self.assertEqual(2, len(self.fx.app.diagnostics.snapshots_page("2000-01-01T00:00:00Z", "2100-01-01T00:00:00Z", None, None, limit=9999)["items"]))
        self.assertEqual(1, len(self.fx.app.diagnostics.traces("2000-01-01T00:00:00Z", "2100-01-01T00:00:00Z", limit=0)["items"]))
        self.assertEqual(2, len(self.fx.app.diagnostics.traces("2000-01-01T00:00:00Z", "2100-01-01T00:00:00Z", limit=9999)["items"]))

    def test_traces_filter_by_model_and_deployment(self):
        self.fx.app.diagnostics.set_switches(snapshots_enabled=True, stats_enabled=False)
        self.fx.app.diagnostics.record_trace("req_f", "received")
        self.fx.app.diagnostics.capture_snapshot("req_f", self.senior["id"], "Senior", "http://127.0.0.1:1/v1",
                                                  "backend", 200, 1.0, None)
        by_model = self.fx.app.diagnostics.traces("2000-01-01T00:00:00Z", "2100-01-01T00:00:00Z", model="Senior")
        self.assertEqual(1, len(by_model["items"]))
        other_model = self.fx.app.diagnostics.traces("2000-01-01T00:00:00Z", "2100-01-01T00:00:00Z", model="Junior")
        self.assertEqual([], other_model["items"])
        by_deployment = self.fx.app.diagnostics.snapshots_page("2000-01-01T00:00:00Z", "2100-01-01T00:00:00Z",
                                                               self.senior["id"], None)
        self.assertEqual(1, len(by_deployment["items"]))


if __name__ == "__main__":
    unittest.main()
