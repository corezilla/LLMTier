"""MT-DIAG-001 — DiagnosticsService 记录与查询（M006，层①，boundary，P1）。

组装保证：trace/快照/统计字段完整、URL 去 query、error_summary 截断 256、
延迟百分位、7 天保留期清理。存储面注入用于回溯旧行（保留期断言）。
"""
from __future__ import annotations

import time
import unittest

from tests.common.fakes import FakeAdapter
from tests.module.cases.support.inference_env import RESPONSE_BODY, InferenceEnv


class RecordQueryTests(InferenceEnv):
    def _enable(self):
        self.fx.app.diagnostics.set_switches(snapshots_enabled=True, stats_enabled=True)

    def _run_request(self, request_id, model="Senior"):
        self.fx.app.responses._test_adapter = FakeAdapter(usage=True)
        try:
            return self.fx.app.responses.create("consumer", request_id, {**RESPONSE_BODY, "model": model})
        finally:
            self.fx.app.responses._test_adapter = None

    def test_trace_view_carries_stages_snapshot_and_usage(self):
        self._enable()
        self._run_request("req_diag_001")
        trace = self._trace_when_complete("req_diag_001")
        self.assertEqual("req_diag_001", trace["request_id"])
        self.assertTrue(trace["stages"])
        # 服务级链的 stage 集合（`received`/`completed` 属 M001 SSE 路径的 stage，
        # 本 Case 经服务方法驱动，不经 handler；stage 顺序不依赖，见 §4 G-OBS-STAGE-ORDER-1）
        self.assertEqual({"validated", "routed", "upstream_started", "upstream_ended"},
                         {s["stage"] for s in trace["stages"]})
        self.assertTrue(trace["snapshot"])
        self.assertTrue(trace["usage"])
        self.assertEqual("measured", trace["usage"]["measurement_status"])

    def _trace_when_complete(self, request_id, timeout=8.0):
        """轮询直到终态 stage 落库（诊断写入与请求返回之间无顺序保证）。"""
        expected = {"validated", "routed", "upstream_started", "upstream_ended"}
        deadline = time.monotonic() + timeout
        trace = None
        while time.monotonic() < deadline:
            try:
                trace = self.fx.app.diagnostics.trace(request_id)
            except Exception:
                time.sleep(0.02)
                continue
            if {s["stage"] for s in trace["stages"]} >= expected:
                return trace
            time.sleep(0.02)
        return trace

    def test_trace_unknown_request_is_404(self):
        with self.assertRaises(Exception) as cm:
            self.fx.app.diagnostics.trace("req_missing")
        self.assertEqual(("not_found", 404), (cm.exception.code, cm.exception.status))

    def test_snapshot_fields_complete_and_url_without_query(self):
        self._enable()
        # 存储面注入：provider endpoint 带 query（去 query 语义）
        self.fx.app.store.connection().execute("UPDATE providers SET endpoint=endpoint||'?token=secret123' WHERE name='cloud-Senior'")
        self._run_request("req_diag_url")
        page = self.fx.app.diagnostics.snapshots_page("2000-01-01T00:00:00Z", "2100-01-01T00:00:00Z", None, None)
        self.assertEqual(1, len(page["items"]))
        item = page["items"][0]
        for field in ("id", "request_id", "captured_at", "upstream_url", "backend_model", "http_status",
                      "latency_ms", "error_summary", "model", "deployment_id", "snapshot_type"):
            self.assertIn(field, item)
        self.assertNotIn("token=secret123", item["upstream_url"])
        self.assertNotIn("secret123", str(item))

    def test_error_summary_truncated_to_256_bytes(self):
        self._enable()
        # http_status=None → snapshot_type=error；非 None → upstream
        snap_id = self.fx.app.diagnostics.capture_snapshot(
            "req_diag_trunc", self.senior["id"], "Senior", "http://127.0.0.1:1/v1", "backend", None, None, "e" * 600)
        self.assertIsNotNone(snap_id)
        page = self.fx.app.diagnostics.snapshots_page("2000-01-01T00:00:00Z", "2100-01-01T00:00:00Z", None, None)
        item = next(i for i in page["items"] if i["id"] == snap_id)
        self.assertEqual(256, len(item["error_summary"].encode()))
        self.assertEqual("error", item["snapshot_type"])
        self.assertIsNone(item["http_status"])

    def test_stats_percentiles_and_status_breakdown(self):
        self._enable()
        for i in range(5):
            self.fx.app.diagnostics.record_latency(self.senior["id"], "Senior", 200, float(10 * (i + 1)))
        data = self.fx.app.diagnostics.stats("2000-01-01T00:00:00Z", "2100-01-01T00:00:00Z")
        self.assertTrue(data["windows"])
        window = data["windows"][0]
        self.assertEqual(5, window["request_count"])
        self.assertEqual(0, window["error_count"])
        # percentile: rank = ceil(p/100 * n), 取该位（sorted）；n=5 → p50→3rd(30), p95→5th(50)
        self.assertEqual(30, window["latency_p50_ms"])
        self.assertEqual(50, window["latency_p95_ms"])
        self.assertEqual(10, window["latency_min_ms"])
        self.assertEqual(50, window["latency_max_ms"])
        self.assertEqual(150, window["latency_sum_ms"])
        self.assertEqual({"200": 5}, window["status_breakdown"])

    def test_stats_error_classification(self):
        self._enable()
        self.fx.app.diagnostics.record_latency(self.senior["id"], "Senior", 404, 5.0)
        self.fx.app.diagnostics.record_latency(self.senior["id"], "Senior", 502, 7.0)
        self.fx.app.diagnostics.record_latency(self.senior["id"], "Senior", None, 9.0)
        data = self.fx.app.diagnostics.stats("2000-01-01T00:00:00Z", "2100-01-01T00:00:00Z")
        window = data["windows"][0]
        self.assertEqual(3, window["request_count"])
        self.assertEqual(1, window["error_4xx_count"])
        self.assertEqual(2, window["error_5xx_count"])  # 502 + upstream_error(None)

    def test_cleanup_removes_rows_older_than_window(self):
        self._enable()
        # 存储面注入：回溯行时间戳（经公开 connection()）
        conn = self.fx.app.store.connection()
        snap_id = self.fx.app.diagnostics.capture_snapshot(
            "req_diag_clean", self.senior["id"], "Senior", "http://127.0.0.1:1/v1", "backend", 200, 1.0, None)
        conn.execute("UPDATE diagnostic_snapshots SET captured_at='2000-01-01T00:00:00.000Z' WHERE id=?", (snap_id,))
        self.fx.app.diagnostics.record_latency(self.senior["id"], "Senior", 200, 1.0)
        conn.execute("UPDATE data_plane_stats SET stat_hour='2000-01-01T00:00:00.000'")
        conn.execute("UPDATE data_plane_latency_samples SET created_at='2000-01-01T00:00:00.000Z'")
        deleted = self.fx.app.diagnostics.cleanup(7)
        self.assertGreaterEqual(deleted, 2)
        self.assertEqual([], self.fx.app.diagnostics.snapshots_page("2000-01-01T00:00:00Z", "2100-01-01T00:00:00Z", None, None)["items"])
        self.assertEqual([], self.fx.app.diagnostics.stats("2000-01-01T00:00:00Z", "2100-01-01T00:00:00Z")["windows"])

    def test_cleanup_keeps_recent_rows(self):
        self._enable()
        self.fx.app.diagnostics.capture_snapshot(
            "req_diag_keep", self.senior["id"], "Senior", "http://127.0.0.1:1/v1", "backend", 200, 1.0, None)
        deleted = self.fx.app.diagnostics.cleanup(7)
        self.assertEqual(0, deleted)
        self.assertEqual(1, len(self.fx.app.diagnostics.snapshots_page("2000-01-01T00:00:00Z", "2100-01-01T00:00:00Z", None, None)["items"]))


if __name__ == "__main__":
    unittest.main()
