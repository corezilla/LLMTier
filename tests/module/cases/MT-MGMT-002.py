"""MT-MGMT-002 — Registry CRUD 组装不变量 + 审计同事务（M004，层①，negative，P0）。

组装保证：ETag stale→412、删除被引用→409 `resource_in_use`、能力冲突→409、
`Embedding-v1` 冻结→409；成功/失败变异均落审计（mutate 与审计同事务）。
"""
from __future__ import annotations

import unittest

from tests.module.cases.support.http_env import LoopbackEnv


class CrudInvariantTests(LoopbackEnv):
    def _create_provider(self, name="prov-x"):
        status, payload, headers = self.request("POST", "/v1/providers",
                                                body={"name": name, "kind": "local", "endpoint": "http://127.0.0.1:9",
                                                      "secret_ref": None, "enabled": True})
        self.assertEqual(201, status)
        return payload, headers["ETag"]

    def _create_deployment(self, name, provider_id):
        caps = {"responses": True, "embeddings": False, "tools": True, "structured_outputs": False,
                "input_modalities": ["text"], "output_modalities": ["text"], "context_window": 128000,
                "max_output_tokens": 16384, "embedding_space_id": None, "embedding_dimensions": None,
                "embedding_max_batch_inputs": None, "embedding_max_input_tokens": None}
        status, payload, headers = self.request("POST", "/v1/deployments",
                                                body={"name": name, "provider_id": provider_id, "backend_model": "m",
                                                      "capabilities": caps, "enabled": True})
        self.assertEqual(201, status)
        return payload, headers["ETag"]

    def _audits(self, action=None):
        _, page, _ = self.request("GET", "/v1/audit?limit=200")
        rows = page["data"]
        return [r for r in rows if action is None or r["action"] == action]

    def test_stale_etag_is_412_with_current_version(self):
        provider, etag = self._create_provider("stale-etag")
        status, payload, _ = self.request("PATCH", f"/v1/providers/{provider['id']}",
                                          body={"name": "renamed"}, headers={"If-Match": etag})
        self.assertEqual(200, status)
        status, payload, _ = self.request("PATCH", f"/v1/providers/{provider['id']}",
                                          body={"name": "again"}, headers={"If-Match": etag})
        self.assertEqual(412, status)
        self.assertEqual("version_conflict", payload["error"]["code"])
        self.assertEqual(2, payload["error"]["current_version"])

    def test_delete_referenced_provider_is_409_in_use(self):
        provider, etag = self._create_provider("in-use")
        self._create_deployment("dep-in-use", provider["id"])
        status, payload, _ = self.request("DELETE", f"/v1/providers/{provider['id']}", headers={"If-Match": etag})
        self.assertEqual(409, status)
        self.assertEqual("resource_in_use", payload["error"]["code"])

    def test_delete_referenced_deployment_is_409_in_use(self):
        provider, _ = self._create_provider("depref")
        deployment, detag = self._create_deployment("depref-dep", provider["id"])
        _, tier_view, _ = self.request("GET", "/v1/service-levels/Worker")
        status, _, _ = self.request("PATCH", "/v1/service-levels/Worker",
                                    body={"deployment_ids": tier_view["deployment_ids"] + [deployment["id"]]},
                                    headers={"If-Match": tier_view["version"] and f'"{tier_view["id"]}.v{tier_view["version"]}"'})
        self.assertEqual(200, status)
        status, payload, _ = self.request("DELETE", f"/v1/deployments/{deployment['id']}", headers={"If-Match": detag})
        self.assertEqual(409, status)
        self.assertEqual("resource_in_use", payload["error"]["code"])

    def test_capability_conflict_on_tier_bind(self):
        provider, _ = self._create_provider("capconf")
        deployment, _ = self._create_deployment("capconf-dep", provider["id"])
        status, payload, _ = self.request("PATCH", "/v1/service-levels/Embedding-v1",
                                          body={"deployment_ids": [deployment["id"]]},
                                          headers={"If-Match": '"Embedding-v1.v1"'})
        self.assertEqual(409, status)
        self.assertIn(payload["error"]["code"], {"capability_conflict", "embedding_space_conflict"})

    def test_audit_records_success_and_failed(self):
        self._create_provider("audited")
        self.assertTrue(any(a["action"] == "provider.create" and a["result"] == "success" for a in self._audits()))
        # 失败变异（stale ETag）→ audit failed 行
        provider, _ = self._create_provider("audited-fail")
        self.request("PATCH", f"/v1/providers/{provider['id']}", body={"name": "x1"},
                     headers={"If-Match": '"wrong.v1"'})
        failed = [a for a in self._audits("provider.update") if a["result"] == "failed"]
        self.assertTrue(failed)
        self.assertTrue(all(a["request_id"] for a in failed))


if __name__ == "__main__":
    unittest.main()
