"""MT-INF-009 — admitted 真/假副作用分支（M003，层②/层④ T1，recovery，P0）。

admitted=True 后失败→`usage.finish(source)` 收敛 final；admitted=False
（准入拒绝，E-INF-ADMIT）→无 finish 副作用（head 停留非 final unknown）。
"""
from __future__ import annotations

import unittest

from http_api.errors import ApiError
from tests.common.fakes import FakeAdapter
from tests.module.cases.support.inference_env import RESPONSE_BODY, InferenceEnv


class AdmittedBranchTests(InferenceEnv):
    def _run(self, request_id, adapter):
        self.fx.app.responses._test_adapter = adapter
        try:
            self.fx.app.responses.create("consumer", request_id, RESPONSE_BODY)
        except ApiError:
            pass
        finally:
            self.fx.app.responses._test_adapter = None

    def _record(self, request_id):
        rows = [r for r in self.usage_rows() if r["request_id"] == request_id]
        return rows[0] if rows else None

    def test_admitted_true_failure_converges_final(self):
        self._run("req_admit_yes", FakeAdapter(fail=ApiError(503, "provider_unavailable", "down", retryable=True)))
        row = self._record("req_admit_yes")
        self.assertIsNotNone(row)
        self.assertTrue(row["is_final"])
        self.assertEqual("unknown", row["measurement_status"])

    def test_admitted_false_rejection_has_no_finish_side_effect(self):
        # 全不健康 → admit 在 yield 前抛出 → admitted=False → 无 finish
        conn = self.fx.app.store.connection()
        conn.execute("UPDATE deployments SET health='unhealthy' WHERE id=?", (self.senior["id"],))
        try:
            self._run("req_admit_no", FakeAdapter())
        finally:
            conn.execute("UPDATE deployments SET health='healthy' WHERE id=?", (self.senior["id"],))
        row = self._record("req_admit_no")
        self.assertIsNotNone(row)
        self.assertFalse(row["is_final"])
        self.assertEqual(("unknown", "unavailable"), (row["measurement_status"], row["source"]))
        self.assertIsNone(row["total_tokens"])
        # 对照：admitted=True 的失败最终收敛（不是同一停留态）
        self._run("req_admit_yes2", FakeAdapter(fail=ApiError(503, "provider_unavailable", "down", retryable=True)))
        converged = self._record("req_admit_yes2")
        self.assertTrue(converged["is_final"])


if __name__ == "__main__":
    unittest.main()
