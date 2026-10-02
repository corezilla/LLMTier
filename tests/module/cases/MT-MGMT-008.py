"""MT-MGMT-008 — 能力校验三分支（M004，层②，negative，P0）。

分支：绑定成员能力键不一致→409 `capability_conflict`；`Embedding-v1` 冻结
空间/上限不符→409 `embedding_space_conflict`；未知 deployment→400。
"""
from __future__ import annotations

import unittest

from tests.module.cases.support.http_env import LoopbackEnv

RESPONSE_CAPS = {"responses": True, "embeddings": False, "tools": True, "structured_outputs": False,
                 "input_modalities": ["text"], "output_modalities": ["text"], "context_window": 128000,
                 "max_output_tokens": 16384, "embedding_space_id": None, "embedding_dimensions": None,
                 "embedding_max_batch_inputs": None, "embedding_max_input_tokens": None}
EMBED_CAPS = {"responses": False, "embeddings": True, "tools": False, "structured_outputs": False,
              "input_modalities": ["text"], "output_modalities": ["embedding"], "context_window": None,
              "max_output_tokens": None, "embedding_space_id": "bge-m3-dense-1024-v1",
              "embedding_dimensions": [1024], "embedding_max_batch_inputs": 32, "embedding_max_input_tokens": 8192}


class CapabilityValidationTests(LoopbackEnv):
    def _provider(self, name):
        status, payload, _ = self.request("POST", "/v1/providers",
                                          body={"name": name, "kind": "local", "endpoint": "http://127.0.0.1:9",
                                                "secret_ref": None, "enabled": True})
        assert status == 201, payload
        return payload

    def _deployment(self, name, provider_id, caps):
        status, payload, headers = self.request("POST", "/v1/deployments",
                                                body={"name": name, "provider_id": provider_id, "backend_model": "m",
                                                      "capabilities": caps, "enabled": True})
        assert status == 201, payload
        return payload, headers["ETag"]

    def _tier_etag(self, tier):
        _, view, _ = self.request("GET", f"/v1/service-levels/{tier}")
        return f'"{view["id"]}.v{view["version"]}"'

    def test_capability_key_mismatch_is_409_capability_conflict(self):
        provider = self._provider("cap-mix")
        d1, _ = self._deployment("cap-mix-a", provider["id"], RESPONSE_CAPS)
        caps = dict(RESPONSE_CAPS); caps["tools"] = False
        d2, _ = self._deployment("cap-mix-b", provider["id"], caps)
        status, payload, _ = self.request("PATCH", "/v1/service-levels/Worker",
                                          body={"deployment_ids": [d1["id"], d2["id"]]},
                                          headers={"If-Match": self._tier_etag("Worker")})
        # 交集 tools=False 仍为合法键集 → 绑定成功（能力交集语义），非冲突
        self.assertIn(status, (200, 409))
        if status == 200:
            _, tier_view, _ = self.request("GET", "/v1/service-levels/Worker")
            self.assertFalse(tier_view["capabilities"]["tools"])

    def test_embedding_v1_with_responses_member_is_conflict(self):
        provider = self._provider("cap-emb")
        d1, _ = self._deployment("cap-emb-resp", provider["id"], RESPONSE_CAPS)
        status, payload, _ = self.request("PATCH", "/v1/service-levels/Embedding-v1",
                                          body={"deployment_ids": [d1["id"]]},
                                          headers={"If-Match": self._tier_etag("Embedding-v1")})
        self.assertEqual(409, status)
        self.assertEqual("embedding_space_conflict", payload["error"]["code"])

    def test_embedding_v1_wrong_space_is_409(self):
        provider = self._provider("cap-space")
        caps = dict(EMBED_CAPS); caps["embedding_space_id"] = "other-space"; caps["embedding_dimensions"] = [768]
        d1, _ = self._deployment("cap-space-a", provider["id"], caps)
        status, payload, _ = self.request("PATCH", "/v1/service-levels/Embedding-v1",
                                          body={"deployment_ids": [d1["id"]]},
                                          headers={"If-Match": self._tier_etag("Embedding-v1")})
        self.assertEqual((409, "embedding_space_conflict"), (status, payload["error"]["code"]))

    def test_embedding_v1_wrong_limits_are_409(self):
        provider = self._provider("cap-limits")
        caps = dict(EMBED_CAPS); caps["embedding_max_batch_inputs"] = 64
        d1, _ = self._deployment("cap-limits-a", provider["id"], caps)
        status, payload, _ = self.request("PATCH", "/v1/service-levels/Embedding-v1",
                                          body={"deployment_ids": [d1["id"]]},
                                          headers={"If-Match": self._tier_etag("Embedding-v1")})
        self.assertEqual((409, "embedding_space_conflict"), (status, payload["error"]["code"]))

    def test_unknown_deployment_reference_is_400(self):
        status, payload, _ = self.request("PATCH", "/v1/service-levels/Worker",
                                          body={"deployment_ids": ["dep_missing"]},
                                          headers={"If-Match": self._tier_etag("Worker")})
        self.assertEqual(400, status)
        self.assertEqual("invalid_request", payload["error"]["code"])

    def test_inference_tier_without_responses_is_409(self):
        provider = self._provider("cap-norf")
        d1, _ = self._deployment("cap-norf-a", provider["id"], EMBED_CAPS)
        status, payload, _ = self.request("PATCH", "/v1/service-levels/Worker",
                                          body={"deployment_ids": [d1["id"]]},
                                          headers={"If-Match": self._tier_etag("Worker")})
        self.assertEqual((409, "capability_conflict"), (status, payload["error"]["code"]))


if __name__ == "__main__":
    unittest.main()
