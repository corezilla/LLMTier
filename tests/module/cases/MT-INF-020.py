"""MT-INF-020 — provider endpoint/secret 变更后新请求接线（M003 组装，层②，normal，P0）。

组装保证：`ResponsesService`/`EmbeddingsService` 的适配器**每请求**从 store
重读 provider 的 `endpoint`/`secret_ref`（`responses.py::_adapter` 与
`embeddings.py::_adapter` 均 `SELECT ... FROM providers`），因此经公开入口
`update_provider(endpoint=...)` 改写上游地址后，**下一次**请求必须打到新上游，
旧上游命中数不再增长。用两个真实 loopback `FakeUpstream`（A/B）各自的
`hits()` 归属命中，锁死"每次重读、不缓存 endpoint/secret"的设计。

环境：ENV-1 组装隔离库 + ENV-3 真实 loopback 假上游（`InferenceEnv` 已把
`Senior` 接到 `self.upstream`=A；本用例另建 B 并以公开入口 `update_provider`
把同一 provider 重指到 B）。
"""
from __future__ import annotations

import unittest

from tests.module.cases.support.inference_env import RESPONSE_BODY, InferenceEnv
from tests.module.cases.support.upstream import FakeUpstream


class EndpointRepointTests(InferenceEnv):
    def setUp(self):
        super().setUp()
        self.other = FakeUpstream(mode="ok")

    def tearDown(self):
        self.other.stop()
        super().tearDown()

    def _cloud_provider(self):
        return next(p for p in self.fx.app.registry.list_providers() if p["name"] == "cloud-Senior")

    def _repoint(self, endpoint):
        provider, etag = self.fx.app.registry.get_provider(self._cloud_provider()["id"])
        self.fx.app.registry.update_provider(provider["id"], {"endpoint": endpoint}, etag)

    def test_endpoint_change_routes_next_request_to_new_upstream(self):
        self.assertEqual((0, 0), (self.upstream.hits(), self.other.hits()))
        self.fx.app.responses.create("consumer", "req_on_a", RESPONSE_BODY)
        self.assertEqual((1, 0), (self.upstream.hits(), self.other.hits()))
        self._repoint(self.other.endpoint)
        self.fx.app.responses.create("consumer", "req_on_b", RESPONSE_BODY)
        self.assertEqual((1, 1), (self.upstream.hits(), self.other.hits()))
        # 再次请求仍只落新上游（无回退到旧值）
        self.fx.app.responses.create("consumer", "req_on_b2", RESPONSE_BODY)
        self.assertEqual((1, 2), (self.upstream.hits(), self.other.hits()))

    def test_secret_change_is_reread_per_request(self):
        import os
        os.environ["LLMTIER_INF020_KEY"] = "sk-new"
        try:
            provider = self._cloud_provider()
            _, etag = self.fx.app.registry.get_provider(provider["id"])
            self.fx.app.registry.update_provider(provider["id"], {"secret_ref": "env:LLMTIER_INF020_KEY"}, etag)
            self.upstream.requests.clear()
            self.fx.app.responses.create("consumer", "req_secret_new", RESPONSE_BODY)
            auths = [headers.get("Authorization") for _, _, headers in self.upstream.requests]
            self.assertIn("Bearer sk-new", auths)
        finally:
            os.environ.pop("LLMTIER_INF020_KEY", None)


if __name__ == "__main__":
    unittest.main()
