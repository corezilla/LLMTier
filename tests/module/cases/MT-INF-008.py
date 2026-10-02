"""MT-INF-008 — 产品注入四态（M003，层②/层③ K4，recovery，P0）。

fault_502→`provider_failure`；fault_503→`provider_unavailable`；
rate_limit→429+`Retry-After`；delay→延迟生效；none→正常。
注入经 M005/M006 公开入口 `set_injections` 配置；命中证据＝账本 source=injected
与 `piko_injected` 标记。
"""
from __future__ import annotations

import time
import unittest

from http_api.errors import ApiError
from tests.common.fakes import FakeAdapter
from tests.module.cases.support.inference_env import RESPONSE_BODY, InferenceEnv


class InjectionTests(InferenceEnv):
    def _set_injection(self, kind, enabled=True, config=None):
        items = [] if kind is None else [{"type": kind, "enabled": enabled, "config": config}]
        return self.fx.app.diagnostics.set_injections(self.senior["id"], items)

    def _create(self, request_id="req_inj"):
        self.fx.app.responses._test_adapter = FakeAdapter(usage=True)
        try:
            return self.fx.app.responses.create("consumer", request_id, RESPONSE_BODY)
        finally:
            self.fx.app.responses._test_adapter = None

    def _create_expect_error(self, request_id="req_inj"):
        self.fx.app.responses._test_adapter = FakeAdapter(usage=True)
        try:
            self.fx.app.responses.create("consumer", request_id, RESPONSE_BODY)
        finally:
            self.fx.app.responses._test_adapter = None

    def test_fault_502_is_provider_failure_and_injected_source(self):
        self._set_injection("fault_502", config={"error_body": "injected boom"})
        with self.assertRaises(ApiError) as cm:
            self._create_expect_error()
        self.assertEqual(("provider_failure", 502), (cm.exception.code, cm.exception.status))
        self.assertEqual({"deployment_id": self.senior["id"], "type": "fault_502"}, cm.exception.piko_injected)
        row = self.head_record("req_inj")
        self.assertEqual("injected", row["source"])
        self.assertEqual("unknown", row["measurement_status"])

    def test_fault_503_is_provider_unavailable(self):
        self._set_injection("fault_503", config={"error_body": "injected down"})
        with self.assertRaises(ApiError) as cm:
            self._create_expect_error("req_inj_503")
        self.assertEqual(("provider_unavailable", 503), (cm.exception.code, cm.exception.status))
        self.assertTrue(cm.exception.retryable)

    def test_rate_limit_injection_is_429_with_retry_after(self):
        self._set_injection("rate_limit", config={"retry_after_sec": 7})
        with self.assertRaises(ApiError) as cm:
            self._create_expect_error("req_inj_rl")
        self.assertEqual(("rate_limit_exceeded", 429), (cm.exception.code, cm.exception.status))
        self.assertEqual("7", cm.exception.headers["Retry-After"])
        self.assertEqual("injected", self.head_record("req_inj_rl")["source"])

    def test_delay_injection_delays_but_succeeds(self):
        self._set_injection("delay", config={"delay_ms": 300})
        t0 = time.monotonic()
        result = self._create("req_inj_delay")
        elapsed = time.monotonic() - t0
        self.assertEqual("completed", result["status"])
        self.assertGreaterEqual(elapsed, 0.25)
        self.assertEqual("measured", self.head_record("req_inj_delay")["measurement_status"])

    def test_none_injection_is_normal(self):
        self._set_injection("fault_502", enabled=False, config={"error_body": "off"})
        result = self._create("req_inj_off")
        self.assertEqual("completed", result["status"])
        self.assertEqual("measured", self.head_record("req_inj_off")["measurement_status"])


if __name__ == "__main__":
    unittest.main()
