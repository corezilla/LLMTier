"""MT-INF-011 — 诊断 fail-open（M003，层②，recovery，P1）。

组装保证：诊断子系统全部写入失败（存储面注入：诊断表不可用，usage 表完好）
时推理结果不变、账本照常 measured、warn 落日志。
（`ResponsesService` 的 `diagnostics` 参数契约＝DiagnosticsService 自身
fail-open；参数抛错不在 VRC-INF-005 语义内，见设计 §14.5。）
"""
from __future__ import annotations

import unittest

from tests.common.fakes import FakeAdapter
from tests.module.cases.support.inference_env import RESPONSE_BODY, InferenceEnv

DIAG_TABLES = ("trace_events", "diagnostic_snapshots", "data_plane_stats", "data_plane_latency_samples")


class FailOpenTests(InferenceEnv):
    def _break_diagnostics_storage(self):
        conn = self.fx.app.store.connection()
        for table in DIAG_TABLES:
            conn.execute(f"DROP TABLE {table}")

    def _warn_events(self):
        page = self.fx.app.logs.page(since="2000-01-01T00:00:00Z", until="2100-01-01T00:00:00Z")
        return [row for row in page["data"] if row["event"] == "capture_failed"]

    def test_diagnostics_write_failure_leaves_inference_unchanged(self):
        # 基线（诊断健康）
        self.fx.app.responses._test_adapter = FakeAdapter(usage=True)
        try:
            baseline = self.fx.app.responses.create("consumer", "req_fo_base", RESPONSE_BODY)
        finally:
            self.fx.app.responses._test_adapter = None
        # 注入：诊断表全部不可用
        self._break_diagnostics_storage()
        self.fx.app.responses._test_adapter = FakeAdapter(usage=True)
        try:
            degraded = self.fx.app.responses.create("consumer", "req_fo_degraded", RESPONSE_BODY)
        finally:
            self.fx.app.responses._test_adapter = None
        self.assertEqual(baseline["status"], degraded["status"])
        self.assertEqual(baseline["output"], degraded["output"])
        self.assertEqual(baseline["usage"], degraded["usage"])
        # fail-open 证据：诊断写失败被记为 warn
        self.assertTrue(self._warn_events())

    def test_ledger_still_measured_with_broken_diagnostics(self):
        self._break_diagnostics_storage()
        self.fx.app.responses._test_adapter = FakeAdapter(usage=True)
        try:
            self.fx.app.responses.create("consumer", "req_fo_ledger", RESPONSE_BODY)
        finally:
            self.fx.app.responses._test_adapter = None
        row = self.head_record("req_fo_ledger")
        self.assertTrue(row["is_final"])
        self.assertEqual("measured", row["measurement_status"])
        self.assertEqual((2, 1, 3), (row["input_tokens"], row["output_tokens"], row["total_tokens"]))


if __name__ == "__main__":
    unittest.main()
