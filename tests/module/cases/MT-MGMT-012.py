"""MT-MGMT-012 — 禁用态 × 请求拒绝（M004 组装，层①，negative，P0）。

组装保证：把 provider / deployment / service level 任一置 `enabled=False`
后，下一次推理请求必须被拒为 404 `model_not_found`（候选 WHERE 要求
`sl.enabled=1 AND d.enabled=1 AND p.enabled=1`，候选为空时 `Router.admit`
抛 404，而不是 503/429）。恢复 `enabled=True` 后请求重新成功，证明拒绝是
禁用态因果。同一禁用态还须让 `GET /v1/models` 的对应 tier
`availability=unavailable`（`ModelCatalog` 读同一 `candidates`，与 UI
`ST-MODEL-*` 联动）。

环境：ENV-1 组装隔离库 + ENV-2 loopback HTTP（`PerTestLoopbackEnv`：每个
test 方法一份全新库，禁用态不会泄漏到相邻用例）。三层初态均经公开入口
（HTTP PATCH）构造，不直写表；推理用 `_test_adapter` 边界替身（`FakeAdapter`）。
"""
from __future__ import annotations

import unittest

from tests.common.fakes import FakeAdapter
from tests.module.cases.support.http_env import PerTestLoopbackEnv

RESPONSE_BODY = {"model": "Worker", "input": "hi", "stream": True, "store": False}


class DisabledStateRejectionTests(PerTestLoopbackEnv):
    def _deployment_id(self):
        return self.fx.app.registry.get_service_level("Worker")[0]["deployment_ids"][0]

    def _provider_id(self):
        return self.fx.app.registry.get_deployment(self._deployment_id())[0]["provider_id"]

    def _call(self):
        self.fx.app.responses._test_adapter = FakeAdapter(usage=True)
        try:
            status, payload, _ = self.request("POST", "/v1/responses", RESPONSE_BODY)
        finally:
            self.fx.app.responses._test_adapter = None
        return status, payload

    def _set_deployment_enabled(self, enabled):
        deployment, _ = self.fx.app.registry.get_deployment(self._deployment_id())
        status, _, _ = self.request("PATCH", f"/v1/deployments/{deployment['id']}",
                                    body={"enabled": enabled},
                                    headers={"If-Match": f'"{deployment["id"]}.v{deployment["version"]}"'})
        self.assertEqual(200, status)

    def _set_provider_enabled(self, enabled):
        provider, _ = self.fx.app.registry.get_provider(self._provider_id())
        status, _, _ = self.request("PATCH", f"/v1/providers/{provider['id']}",
                                    body={"enabled": enabled},
                                    headers={"If-Match": f'"{provider["id"]}.v{provider["version"]}"'})
        self.assertEqual(200, status)

    def _set_service_level_enabled(self, enabled):
        level, _ = self.fx.app.registry.get_service_level("Worker")
        status, _, _ = self.request("PATCH", "/v1/service-levels/Worker",
                                    body={"enabled": enabled},
                                    headers={"If-Match": f'"Worker.v{level["version"]}"'})
        self.assertEqual(200, status)

    def _availability(self, tier="Worker"):
        status, payload, _ = self.request("GET", "/v1/models")
        self.assertEqual(200, status)
        return next(m for m in payload["data"] if m["id"] == tier)["availability"]

    def _assert_disabled_then_restored(self, setter):
        status, payload = self._call()
        self.assertEqual(200, status, payload)
        setter(False)
        status, payload, _ = self.request("POST", "/v1/responses", RESPONSE_BODY)
        self.assertEqual(404, status)
        self.assertEqual("model_not_found", payload["error"]["code"])
        self.assertEqual("unavailable", self._availability())
        setter(True)
        status, payload = self._call()
        self.assertEqual(200, status, payload)

    def test_disabled_deployment_rejects_request_404_then_restores(self):
        self._assert_disabled_then_restored(self._set_deployment_enabled)

    def test_disabled_provider_rejects_request_404_then_restores(self):
        self._assert_disabled_then_restored(self._set_provider_enabled)

    def test_disabled_service_level_rejects_request_404_then_restores(self):
        self._assert_disabled_then_restored(self._set_service_level_enabled)


if __name__ == "__main__":
    unittest.main()
