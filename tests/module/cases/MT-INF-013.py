"""MT-INF-013 — stall/hang 上游永不响应（M003，层②，recovery，P0；§1.5.1 c1）。

loopback 假上游 accept 后不回字节；`connect_timeout_ms` 置小（存储面注入，
方案 c1 预设）→ 503 `provider_unavailable`（retryable）；账本 `unknown` 收敛、
Router 许可释放。
"""
from __future__ import annotations

import unittest

from http_api.errors import ApiError
from tests.module.cases.support.inference_env import RESPONSE_BODY, InferenceEnv


class StallTests(InferenceEnv):
    def test_stalled_upstream_times_out_as_503(self):
        self.set_timeouts(connect_ms=400, idle_ms=500)
        self.upstream_mode("stall")
        with self.assertRaises(ApiError) as cm:
            self.fx.app.responses.create("consumer", "req_stall", RESPONSE_BODY)
        self.assertEqual(("provider_unavailable", 503), (cm.exception.code, cm.exception.status))
        self.assertTrue(cm.exception.retryable)
        row = self.head_record("req_stall")
        self.assertTrue(row["is_final"])
        self.assertEqual("unknown", row["measurement_status"])

    def test_permit_released_after_stall_timeout(self):
        self.set_timeouts(connect_ms=300, idle_ms=400)
        self.upstream_mode("stall")
        with self.assertRaises(ApiError):
            self.fx.app.responses.create("consumer", "req_stall2", RESPONSE_BODY)
        deadline = None
        import time as _time
        deadline = _time.monotonic() + 5
        while _time.monotonic() < deadline:
            if sum(self.fx.app.router.snapshot()["queues"].values()) == 0 and \
               sum(v["running"] for v in self.fx.app.router.snapshot()["deployments"].values()) == 0:
                break
            _time.sleep(0.05)
        snapshot = self.fx.app.router.snapshot()
        self.assertEqual(0, sum(v["running"] for v in snapshot["deployments"].values()))

    def test_subsequent_request_recovers_after_stall(self):
        self.set_timeouts(connect_ms=400, idle_ms=500)
        self.upstream_mode("stall")
        with self.assertRaises(ApiError):
            self.fx.app.responses.create("consumer", "req_stall3", RESPONSE_BODY)
        self.upstream_mode("ok")
        result = self.fx.app.responses.create("consumer", "req_after_stall", RESPONSE_BODY)
        self.assertEqual("completed", result["status"])


if __name__ == "__main__":
    unittest.main()
