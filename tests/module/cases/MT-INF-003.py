"""MT-INF-003 — UsageRecorder 账本组装后失败与用量（M003，层①，recovery，P0）。

组装保证：上游 5xx/超时→`provider_unavailable`；usage 缺失→unknown 不补零；
账本终态单调推进（T1/T2/T3 迁移）。注入＝边界替身（FakeAdapter fail）。
"""
from __future__ import annotations

import unittest

from http_api.errors import ApiError
from tests.common.fakes import FakeAdapter
from tests.module.cases.support.inference_env import RESPONSE_BODY, InferenceEnv


class UsageLedgerTests(InferenceEnv):
    def _create(self, adapter):
        self.fx.app.responses._test_adapter = adapter
        try:
            return self.fx.app.responses.create("consumer", "req_ledger", RESPONSE_BODY)
        finally:
            self.fx.app.responses._test_adapter = None

    def _create_expect_error(self, adapter):
        self.fx.app.responses._test_adapter = adapter
        try:
            self.fx.app.responses.create("consumer", "req_ledger", RESPONSE_BODY)
        finally:
            self.fx.app.responses._test_adapter = None

    def test_measured_finish_is_final(self):
        self._create(FakeAdapter(usage=True))
        row = self.head_record()
        self.assertTrue(row["is_final"])
        self.assertEqual(("measured", "provider"), (row["measurement_status"], row["source"]))

    def test_missing_usage_is_unknown_not_zero(self):
        self._create(FakeAdapter(usage=False))
        row = self.head_record()
        self.assertTrue(row["is_final"])
        self.assertEqual(("unknown", "unavailable"), (row["measurement_status"], row["source"]))
        self.assertIsNone(row["input_tokens"]); self.assertIsNone(row["output_tokens"]); self.assertIsNone(row["total_tokens"])

    def test_upstream_5xx_maps_503_and_ledger_unknown(self):
        with self.assertRaises(ApiError) as cm:
            self._create_expect_error(FakeAdapter(fail=ApiError(503, "provider_unavailable", "upstream down", retryable=True)))
        self.assertEqual(("provider_unavailable", 503), (cm.exception.code, cm.exception.status))
        row = self.head_record()
        self.assertTrue(row["is_final"])
        self.assertEqual("unknown", row["measurement_status"])
        self.assertIsNone(row["total_tokens"])

    def test_upstream_timeout_leaves_ledger_unknown(self):
        # TimeoutError 在服务层原样传播（→503 的 transport 映射由 MT-INF-013 承接）；
        # 组装保证＝义务收敛为 unknown，不补零
        with self.assertRaises(TimeoutError):
            self._create_expect_error(FakeAdapter(fail=TimeoutError("upstream timeout")))
        row = self.head_record()
        self.assertTrue(row["is_final"])
        self.assertEqual("unknown", row["measurement_status"])
        self.assertIsNone(row["total_tokens"])

    def test_ledger_advances_across_requests(self):
        with self.assertRaises(ApiError):
            self._create_expect_error(FakeAdapter(fail=ApiError(503, "provider_unavailable", "x", retryable=True)))
        first = self.head_record()
        self.assertTrue(first["is_final"])
        self.assertEqual("unknown", first["measurement_status"])
        self.fx.app.responses.create("consumer", "req_ledger_ok", RESPONSE_BODY)
        second = self.head_record()
        self.assertEqual("req_ledger_ok", second["request_id"])
        self.assertEqual("measured", second["measurement_status"])
        self.assertTrue(second["is_final"])
        self.assertNotEqual(first["request_id"], second["request_id"])


if __name__ == "__main__":
    unittest.main()
