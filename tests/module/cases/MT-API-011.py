"""MT-API-011 — 鉴权结果 × 端点类别组合（M001，层③ K1，security，P0）。

pairwise 组合行：(data-ok, data 端点)→200 / (admin-ok, admin 端点)→200 /
(data-cred, admin 端点)→403 / (无有效凭据, 任一端点)→401 / (未配置, 任一端点)→503。
组装路径上拒绝先于业务（403 后无半写）。
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from tests.module.cases.support.http_env import LoopbackEnv


def os_environ():
    import os
    return os.environ


class AuthPairwiseTests(LoopbackEnv):
    ENV = {"LLMTIER_ADMIN_TOKEN": "admin-secret", "LLMTIER_DATA_TOKEN": "data-secret"}

    def test_data_credential_on_data_endpoint_is_200(self):
        with patch.dict(os_environ(), self.ENV, clear=False):
            status, payload, _ = self.request("GET", "/v1/models", headers={"Authorization": "Bearer data-secret"})
        self.assertEqual(200, status)

    def test_admin_credential_on_admin_endpoint_is_200(self):
        with patch.dict(os_environ(), self.ENV, clear=False):
            status, payload, _ = self.request("GET", "/v1/providers", headers={"Authorization": "Bearer admin-secret"})
        self.assertEqual(200, status)

    def test_data_credential_on_admin_endpoint_is_403(self):
        with patch.dict(os_environ(), self.ENV, clear=False):
            status, payload, _ = self.request("GET", "/v1/providers", headers={"Authorization": "Bearer data-secret"})
        self.assertEqual(403, status)
        self.assertEqual("permission_denied", payload["error"]["code"])

    def test_invalid_credential_shape_is_401(self):
        with patch.dict(os_environ(), self.ENV, clear=False):
            status, payload, _ = self.request("GET", "/v1/models", headers={"Authorization": "bearer data-secret"})
        self.assertEqual(401, status)
        self.assertEqual("authentication_required", payload["error"]["code"])

    def test_unconfigured_bearer_is_503(self):
        env = {"LLMTIER_ADMIN_TOKEN": "", "LLMTIER_DATA_TOKEN": ""}
        with patch.dict(os_environ(), env, clear=False):
            for path in ("/v1/models", "/v1/providers"):
                status, payload, _ = self.request("GET", path, headers={"Authorization": "Bearer x"})
                self.assertEqual(503, status, path)
                self.assertEqual("auth_not_configured", payload["error"]["code"])

    def test_rejection_precedes_business_no_half_write(self):
        with patch.dict(os_environ(), self.ENV, clear=False):
            status, payload, _ = self.request("POST", "/v1/providers",
                                              body={"name": "rogue", "kind": "local", "endpoint": "http://127.0.0.1:9",
                                                    "secret_ref": None, "enabled": True},
                                              headers={"Authorization": "Bearer data-secret"})
            self.assertEqual(403, status)
            _, providers, _ = self.request("GET", "/v1/providers", headers={"Authorization": "Bearer admin-secret"})
        self.assertFalse(any(p["name"] == "rogue" for p in providers["data"]))


if __name__ == "__main__":
    unittest.main()
