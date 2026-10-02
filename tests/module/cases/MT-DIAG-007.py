"""MT-DIAG-007 — fail-open 分支（M006，层②，recovery，P1）。

各写入失败（record_trace/capture_snapshot/record_latency）不阻断推理、
落 warn；cleanup 失败返回 0。存储面注入（DROP 诊断表）触发。
（`_UnavailableDiagnostics` 降级分支由 UT-API-005 覆盖——无公开入口可触发
其构造失败，本层不重复登记。）
"""
from __future__ import annotations

import unittest

from tests.common.fakes import FakeAdapter
from tests.module.cases.support.inference_env import RESPONSE_BODY, InferenceEnv

DIAG_TABLES = ("trace_events", "diagnostic_snapshots", "data_plane_stats", "data_plane_latency_samples")


class FailOpenTests(InferenceEnv):
    def _break(self):
        conn = self.fx.app.store.connection()
        for table in DIAG_TABLES:
            conn.execute(f"DROP TABLE {table}")

    def _warns(self):
        page = self.fx.app.logs.page(since="2000-01-01T00:00:00Z", until="2100-01-01T00:00:00Z")
        return [row for row in page["data"] if row["event"] == "capture_failed"]

    def test_write_failures_do_not_raise(self):
        self._break()
        self.fx.app.diagnostics.record_trace("req_fo", "received", {"a": 1})
        self.fx.app.diagnostics.capture_snapshot("req_fo", self.senior["id"], "Senior", "http://127.0.0.1:1/v1",
                                                  "backend", 200, 1.0, "err")
        self.fx.app.diagnostics.record_latency(self.senior["id"], "Senior", 200, 1.0)
        self.assertTrue(self._warns())

    def test_inference_unaffected_by_broken_diagnostics(self):
        self.fx.app.diagnostics.set_switches(snapshots_enabled=True, stats_enabled=True)
        self._break()
        self.fx.app.responses._test_adapter = FakeAdapter(usage=True)
        try:
            result = self.fx.app.responses.create("consumer", "req_fo_2", RESPONSE_BODY)
        finally:
            self.fx.app.responses._test_adapter = None
        self.assertEqual("completed", result["status"])
        self.assertTrue(result["output"])

    def test_cleanup_failure_returns_zero(self):
        self._break()
        self.assertEqual(0, self.fx.app.diagnostics.cleanup(7))
        self.assertTrue(self._warns())

    def test_capture_snapshot_returns_none_on_write_failure(self):
        self._break()
        self.assertIsNone(self.fx.app.diagnostics.capture_snapshot(
            "req_fo_3", self.senior["id"], "Senior", "http://127.0.0.1:1/v1", "backend", 200, 1.0, None))

    def test_switches_still_readable_after_write_failures(self):
        self.fx.app.diagnostics.set_switches(snapshots_enabled=True, stats_enabled=True)
        self._break()
        self.assertEqual({"snapshots_enabled": True, "stats_enabled": True}, self.fx.app.diagnostics.switches())


if __name__ == "__main__":
    unittest.main()
