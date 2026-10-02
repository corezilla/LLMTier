"""MT-MGMT-013 — `/v1/providers/{id}/models` 功能行为（M004 组装，层①，negative，P1）。

组装保证：`GET /v1/providers/{id}/models`（`app.py` → `AdminService.list_provider_models`
→ `provider.list_models()`）真实打通到上游 `/models`；上游返回合法目录→200
`{"data":[id,...]}`；返回含缺失/非字符串 `id` 的坏目录→仅保留合法字符串 id
（核对 `openai.py::list_models` 的 `[m["id"] for m in payload.get("data",[]) if isinstance(m.get("id"), str)]`）；
上游 5xx→503 `provider_unavailable`；未知 provider→404 `not_found`。

环境：ENV-1 组装隔离库 + ENV-2 loopback HTTP + ENV-3 可编程 loopback 假上游
（`PerTestLoopbackEnv` + `FakeUpstream(models_mode=...)`：`ok`/`mixed`/`error`）。
provider 经公开入口 `POST /v1/providers`（`kind=cloud`，`endpoint` 指向假上游）建初态；
不直写表、不改 `src/`。
"""
from __future__ import annotations

import unittest

from tests.module.cases.support.http_env import PerTestLoopbackEnv
from tests.module.cases.support.upstream import FakeUpstream


class ProviderModelsTests(PerTestLoopbackEnv):
    def setUp(self):
        super().setUp()
        self.upstream = FakeUpstream(mode="ok")

    def tearDown(self):
        self.upstream.stop()
        super().tearDown()

    def _provider(self, name="models-provider"):
        status, payload, _ = self.request("POST", "/v1/providers",
                                          body={"name": name, "kind": "cloud", "endpoint": self.upstream.endpoint,
                                                "secret_ref": None, "enabled": True})
        self.assertEqual(201, status)
        return payload

    def _models(self, provider_id):
        return self.request("GET", f"/v1/providers/{provider_id}/models")

    def test_valid_catalog_returns_id_list(self):
        provider = self._provider()
        status, payload, _ = self._models(provider["id"])
        self.assertEqual(200, status)
        self.assertEqual({"data"}, set(payload))
        self.assertEqual(["backend"], payload["data"])

    def test_bad_entries_are_filtered_to_valid_ids(self):
        self.upstream.models_mode = "mixed"
        provider = self._provider("models-mixed")
        status, payload, _ = self._models(provider["id"])
        self.assertEqual(200, status)
        self.assertEqual(["backend", "second"], payload["data"])

    def test_non_object_entry_is_filtered_not_500(self):
        # E-PROVIDER-CATALOG: 上游 data 含非 dict 元素（字符串/数字/None）时，
        # 目录解析必须过滤掉它们而不是抛 AttributeError → 组装层 500。
        self.upstream.models_mode = "non_dict"
        provider = self._provider("models-non-dict")
        status, payload, _ = self._models(provider["id"])
        self.assertEqual(200, status)
        self.assertEqual(["backend"], payload["data"])

    def test_upstream_5xx_is_503_provider_unavailable(self):
        self.upstream.models_mode = "error"
        provider = self._provider("models-error")
        status, payload, _ = self._models(provider["id"])
        self.assertEqual(503, status)
        self.assertEqual("provider_unavailable", payload["error"]["code"])
        self.assertTrue(payload["error"]["retryable"])

    def test_unknown_provider_is_404(self):
        status, payload, _ = self._models("provider_missing")
        self.assertEqual(404, status)
        self.assertEqual("not_found", payload["error"]["code"])


if __name__ == "__main__":
    unittest.main()
