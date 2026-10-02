"""MT-INF-006 — 能力分支 × 请求形态（M003，层②/层③ K5，negative，P0）。

分支：能力档 `responses=false`→`unsupported_model`；带 tools 但能力不支持→
`unsupported_request`；`max_output_tokens` 越界/非整数→`invalid_request`。
"""
from __future__ import annotations

import unittest

from http_api.errors import ApiError
from tests.common.fakes import FakeAdapter, response_capabilities
from tests.module.cases.support.inference_env import InferenceEnv

BASE = {"input": "hi", "stream": True, "store": False}


class CapabilityTests(InferenceEnv):
    def _wire(self, tier, caps):
        provider, _ = self.fx.app.registry.create_provider(
            {"name": f"p-{tier}-{caps.get('responses')}", "kind": "local", "endpoint": "http://127.0.0.1:9",
             "secret_ref": None, "enabled": True})
        deployment, _ = self.fx.app.registry.create_deployment(
            {"name": f"d-{tier}-{caps.get('responses')}", "provider_id": provider["id"], "backend_model": "m",
             "capabilities": caps, "enabled": True})
        view, etag = self.fx.app.registry.get_service_level(tier)
        self.fx.app.registry.update_service_level(tier, {"deployment_ids": [deployment["id"]]}, etag)
        self.fx.app.store.connection().execute("UPDATE deployments SET health='healthy' WHERE id=?", (deployment["id"],))

    def _create(self, body):
        self.fx.app.responses._test_adapter = FakeAdapter()
        try:
            return self.fx.app.responses.create("consumer", "req_cap", body)
        finally:
            self.fx.app.responses._test_adapter = None

    def test_responses_false_is_unsupported_model(self):
        # 能力档 responses=false 的真实来源＝未绑定成员的空 tier（ensure_fixed_tiers 缺省能力）
        with self.assertRaises(ApiError) as cm:
            self._create({**BASE, "model": "Junior"})
        self.assertEqual(("unsupported_model", 400, "model"), (cm.exception.code, cm.exception.status, cm.exception.param))

    def test_tools_without_capability_is_unsupported_request(self):
        caps = response_capabilities(); caps["tools"] = False
        self._wire("Associate", caps)
        with self.assertRaises(ApiError) as cm:
            self._create({**BASE, "model": "Associate", "tools": [{"type": "function"}]})
        self.assertEqual(("unsupported_request", 400, "tools"), (cm.exception.code, cm.exception.status, cm.exception.param))

    def test_max_output_tokens_out_of_range(self):
        caps = response_capabilities(); caps["max_output_tokens"] = 100
        self._wire("Engineer", caps)
        for value in (0, -1, 101):
            with self.assertRaises(ApiError) as cm:
                self._create({**BASE, "model": "Engineer", "max_output_tokens": value})
            self.assertEqual(("invalid_request", "max_output_tokens"), (cm.exception.code, cm.exception.param))

    def test_max_output_tokens_non_integer_rejected(self):
        caps = response_capabilities(); caps["max_output_tokens"] = 100
        self._wire("Executor", caps)
        with self.assertRaises(ApiError) as cm:
            self._create({**BASE, "model": "Executor", "max_output_tokens": "50"})
        self.assertEqual("invalid_request", cm.exception.code)
        with self.assertRaises(ApiError) as cm:
            self._create({**BASE, "model": "Executor", "max_output_tokens": True})
        self.assertEqual("invalid_request", cm.exception.code)


if __name__ == "__main__":
    unittest.main()
