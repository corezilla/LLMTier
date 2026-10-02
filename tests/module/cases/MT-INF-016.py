"""MT-INF-016 — 截断流 early EOF（M003，层②，recovery，P0；§1.5.1 c6）。

上游在 terminal 事件前 EOF → 502 `provider_contract_error`（无合法 terminal）；
账本收敛 unknown 不补零。
"""
from __future__ import annotations

import unittest

from http_api.errors import ApiError
from tests.module.cases.support.inference_env import RESPONSE_BODY, InferenceEnv


class TruncatedStreamTests(InferenceEnv):
    def test_early_eof_is_502_contract_error(self):
        self.upstream_mode("truncated")
        with self.assertRaises(ApiError) as cm:
            self.fx.app.responses.create("consumer", "req_trunc", RESPONSE_BODY)
        self.assertEqual(("provider_contract_error", 502), (cm.exception.code, cm.exception.status))
        row = self.head_record("req_trunc")
        self.assertTrue(row["is_final"])
        self.assertEqual("unknown", row["measurement_status"])
        self.assertIsNone(row["total_tokens"])

    def test_stream_recovery_after_truncation(self):
        self.upstream_mode("truncated")
        with self.assertRaises(ApiError):
            self.fx.app.responses.create("consumer", "req_trunc2", RESPONSE_BODY)
        self.upstream_mode("ok")
        result = self.fx.app.responses.create("consumer", "req_ok_trunc", RESPONSE_BODY)
        self.assertEqual("completed", result["status"])


if __name__ == "__main__":
    unittest.main()
