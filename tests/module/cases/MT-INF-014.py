"""MT-INF-014 — slow-response 流空闲超时（M003，层②，recovery，P1；§1.5.1 c2）。

上游分片慢发、片间隔 > `stream_idle_timeout_ms`（存储面注入置小）→
503 `provider_unavailable`；无半写账本、许可释放。
"""
from __future__ import annotations

import time
import unittest

from http_api.errors import ApiError
from tests.module.cases.support.inference_env import RESPONSE_BODY, InferenceEnv


class SlowResponseTests(InferenceEnv):
    def test_trickle_beyond_idle_timeout_is_503(self):
        self.set_timeouts(connect_ms=5000, idle_ms=400)
        self.upstream_mode("trickle", chunk_delay=0.7, events=3)
        t0 = time.monotonic()
        with self.assertRaises(ApiError) as cm:
            self.fx.app.responses.create("consumer", "req_slow", RESPONSE_BODY)
        elapsed = time.monotonic() - t0
        self.assertEqual(("provider_unavailable", 503), (cm.exception.code, cm.exception.status))
        self.assertTrue(cm.exception.retryable)
        self.assertLess(elapsed, 5)
        row = self.head_record("req_slow")
        self.assertTrue(row["is_final"])
        self.assertEqual("unknown", row["measurement_status"])

    def test_permit_released_after_slow_timeout(self):
        self.set_timeouts(connect_ms=5000, idle_ms=300)
        self.upstream_mode("trickle", chunk_delay=0.6, events=2)
        with self.assertRaises(ApiError):
            self.fx.app.responses.create("consumer", "req_slow2", RESPONSE_BODY)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            snapshot = self.fx.app.router.snapshot()
            if sum(v["running"] for v in snapshot["deployments"].values()) == 0:
                break
            time.sleep(0.05)
        snapshot = self.fx.app.router.snapshot()
        self.assertEqual(0, sum(v["running"] for v in snapshot["deployments"].values()))


if __name__ == "__main__":
    unittest.main()
