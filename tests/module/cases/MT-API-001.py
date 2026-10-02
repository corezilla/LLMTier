"""MT-API-001 — 组装后路由分发/统一错误信封/健康就绪（M001，层①，normal，P0）。

组装保证：请求经真实 handler 栈（鉴权→路由→服务→存储）命中端点；错误信封
键集与 `X-Request-ID` 统一；/healthz、/readyz（就绪语义）一致。
"""
from __future__ import annotations

import unittest

from tests.module.cases.support.http_env import LoopbackEnv


class DispatchAssemblyTests(LoopbackEnv):
    def test_healthz_view(self):
        status, payload, headers = self.request("GET", "/healthz")
        self.assertEqual(200, status)
        self.assertEqual({"status": "ok", "version": payload["version"]}, payload)
        self.assertTrue(headers.get("X-Request-ID"))

    def test_readyz_after_seed_maps_degraded(self):
        # 仅播种 Worker 一个 tier：Worker available、其余 unavailable → degraded/503
        status, payload, _ = self.request("GET", "/readyz")
        self.assertEqual(503, status)
        self.assertEqual("degraded", payload["status"])
        tiers = {m["id"]: m["availability"] for m in payload["models"]}
        self.assertEqual("available", tiers["Worker"])
        self.assertEqual("unavailable", tiers["Senior"])

    def test_models_route_hits_service_and_store(self):
        status, payload, _ = self.request("GET", "/v1/models")
        self.assertEqual(200, status)
        ids = [m["id"] for m in payload["data"]]
        self.assertIn("Worker", ids)
        worker = next(m for m in payload["data"] if m["id"] == "Worker")
        self.assertEqual("available", worker["availability"])

    def test_error_envelope_is_uniform(self):
        status, payload, headers = self.request("POST", "/v1/responses", body={"model": "Worker"})
        self.assertEqual(400, status)
        err = payload["error"]
        self.assertEqual({"message", "type", "code", "param", "retryable"}, set(err))
        self.assertEqual("request_error", err["type"])
        self.assertTrue(headers.get("X-Request-ID"))


if __name__ == "__main__":
    unittest.main()
