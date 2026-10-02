"""MT-MGMT-007 — CRUD 五错误分支 + 资源版本迁移（M004，层②/层③ K6/层④ T8，negative，P0）。

K6 组合行：(provider,412)/(deployment,412)/(service_level,409-conflict)/
(provider,409-in-use)/(deployment,409-in-use)/(任一类,404)；
T8：vN→vN+1（ETag 变化），旧 ETag→412；deployment provider_id 变更→400。
"""
from __future__ import annotations

import unittest

from tests.module.cases.support.http_env import LoopbackEnv


class CrudBranchMatrixTests(LoopbackEnv):
    def _provider(self, name):
        status, payload, headers = self.request("POST", "/v1/providers",
                                                body={"name": name, "kind": "local", "endpoint": "http://127.0.0.1:9",
                                                      "secret_ref": None, "enabled": True})
        assert status == 201, payload
        return payload, headers["ETag"]

    def _deployment(self, name, provider_id):
        caps = {"responses": True, "embeddings": False, "tools": True, "structured_outputs": False,
                "input_modalities": ["text"], "output_modalities": ["text"], "context_window": 128000,
                "max_output_tokens": 16384, "embedding_space_id": None, "embedding_dimensions": None,
                "embedding_max_batch_inputs": None, "embedding_max_input_tokens": None}
        status, payload, headers = self.request("POST", "/v1/deployments",
                                                body={"name": name, "provider_id": provider_id, "backend_model": "m",
                                                      "capabilities": caps, "enabled": True})
        assert status == 201, payload
        return payload, headers["ETag"]

    def test_provider_stale_etag_412(self):
        provider, etag = self._provider("k6-p1")
        self.request("PATCH", f"/v1/providers/{provider['id']}", body={"name": "k6-p1b"}, headers={"If-Match": etag})
        status, payload, _ = self.request("PATCH", f"/v1/providers/{provider['id']}", body={"name": "k6-p1c"},
                                          headers={"If-Match": etag})
        self.assertEqual((412, "version_conflict"), (status, payload["error"]["code"]))

    def test_deployment_stale_etag_412(self):
        provider, _ = self._provider("k6-p2")
        deployment, etag = self._deployment("k6-d2", provider["id"])
        self.request("PATCH", f"/v1/deployments/{deployment['id']}", body={"name": "k6-d2b"}, headers={"If-Match": etag})
        status, payload, _ = self.request("PATCH", f"/v1/deployments/{deployment['id']}", body={"name": "k6-d2c"},
                                          headers={"If-Match": etag})
        self.assertEqual((412, "version_conflict"), (status, payload["error"]["code"]))

    def test_service_level_duplicate_conflict_409(self):
        _, worker, _ = self.request("GET", "/v1/service-levels/Worker")
        status, payload, _ = self.request("POST", "/v1/service-levels",
                                          body={"id": "Worker", "deployment_ids": worker["deployment_ids"],
                                                "enabled": True})
        self.assertEqual((409, "resource_conflict"), (status, payload["error"]["code"]))

    def test_service_level_empty_members_is_400(self):
        status, payload, _ = self.request("POST", "/v1/service-levels",
                                          body={"id": "Senior", "deployment_ids": [], "enabled": True})
        self.assertEqual((400, "invalid_request"), (status, payload["error"]["code"]))
        self.assertEqual("deployment_ids", payload["error"]["param"])

    def test_provider_in_use_409(self):
        provider, etag = self._provider("k6-p3")
        self._deployment("k6-d3", provider["id"])
        status, payload, _ = self.request("DELETE", f"/v1/providers/{provider['id']}", headers={"If-Match": etag})
        self.assertEqual((409, "resource_in_use"), (status, payload["error"]["code"]))

    def test_deployment_in_use_409(self):
        provider, _ = self._provider("k6-p4")
        deployment, detag = self._deployment("k6-d4", provider["id"])
        _, tier, _ = self.request("GET", "/v1/service-levels/Worker")
        tier_etag = f'"{tier["id"]}.v{tier["version"]}"'
        status, _, _ = self.request("PATCH", "/v1/service-levels/Worker",
                                    body={"deployment_ids": tier["deployment_ids"] + [deployment["id"]]},
                                    headers={"If-Match": tier_etag})
        self.assertEqual(200, status)
        status, payload, _ = self.request("DELETE", f"/v1/deployments/{deployment['id']}", headers={"If-Match": detag})
        self.assertEqual((409, "resource_in_use"), (status, payload["error"]["code"]))

    def test_unknown_resources_are_404(self):
        for path, method, body, headers in (
            ("/v1/providers/px_missing", "PATCH", {"name": "x"}, {"If-Match": '"px_missing.v1"'}),
            ("/v1/deployments/dx_missing", "DELETE", None, {"If-Match": '"dx_missing.v1"'}),
            ("/v1/service-levels/nope", "GET", None, {}),
        ):
            status, payload, _ = self.request(method, path, body=body, headers=headers)
            self.assertEqual((404, "not_found"), (status, payload["error"]["code"]), path)

    def test_version_transitions_and_provider_id_immutable(self):
        provider, etag1 = self._provider("t8-p")
        status, view1, headers = self.request("GET", f"/v1/providers/{provider['id']}")
        self.assertEqual(1, view1["version"])
        status, view2, _ = self.request("PATCH", f"/v1/providers/{provider['id']}", body={"name": "t8-p2"},
                                        headers={"If-Match": etag1})
        self.assertEqual(2, view2["version"])
        self.assertNotEqual(etag1, f'"{provider["id"]}.v2"')
        # deployment provider_id 变更 → 400
        provider2, _ = self._provider("t8-p-b")
        deployment, detag = self._deployment("t8-d", provider["id"])
        status, payload, _ = self.request("PATCH", f"/v1/deployments/{deployment['id']}",
                                          body={"provider_id": provider2["id"]}, headers={"If-Match": detag})
        self.assertEqual((400, "invalid_request"), (status, payload["error"]["code"]))
        self.assertEqual("provider_id", payload["error"]["param"])

    def test_duplicate_names_are_409_conflict(self):
        self._provider("dup-name")
        status, payload, _ = self.request("POST", "/v1/providers",
                                          body={"name": "dup-name", "kind": "local", "endpoint": "http://127.0.0.1:9",
                                                "secret_ref": None, "enabled": True})
        self.assertEqual((409, "resource_conflict"), (status, payload["error"]["code"]))


if __name__ == "__main__":
    unittest.main()
