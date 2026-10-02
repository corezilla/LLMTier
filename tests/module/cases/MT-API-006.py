"""MT-API-006 — `_auth` 三态 401/403/503 + `_auth_either` 优先级（M001，层②，security，P0）。

三态：凭据未配置+Bearer→503 `auth_not_configured`；非 Bearer→401；凭据错误→403。
`_auth_either`：admin 先于 data 匹配；data 凭据落共享端点角色为 data。
配置注入＝进程环境变量（模块边界配置），无内部打桩。
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from tests.module.cases.support.http_env import LoopbackEnv


class AuthStateTests(LoopbackEnv):
    def test_bearer_without_config_is_503_auth_not_configured(self):
        with patch.dict(os_environ(), {"LLMTIER_ADMIN_TOKEN": "", "LLMTIER_DATA_TOKEN": ""}, clear=False):
            status, payload, _ = self.request("GET", "/v1/models", headers={"Authorization": "Bearer anything"})
            self.assertEqual(503, status)
            self.assertEqual("auth_not_configured", payload["error"]["code"])

    def test_non_bearer_authorization_is_401(self):
        with patch.dict(os_environ(), {"LLMTIER_ADMIN_TOKEN": "admin-secret"}, clear=False):
            status, payload, _ = self.request("GET", "/v1/providers", headers={"Authorization": "Basic abc"})
            self.assertEqual(401, status)
            self.assertEqual("authentication_required", payload["error"]["code"])

    def test_wrong_bearer_is_403(self):
        with patch.dict(os_environ(), {"LLMTIER_ADMIN_TOKEN": "admin-secret"}, clear=False):
            status, payload, _ = self.request("GET", "/v1/providers", headers={"Authorization": "Bearer nope"})
            self.assertEqual(403, status)
            self.assertEqual("permission_denied", payload["error"]["code"])

    def test_loopback_without_authorization_is_trusted(self):
        status, payload, _ = self.request("GET", "/v1/models")
        self.assertEqual(200, status)


class AuthEitherTests(LoopbackEnv):
    def _env(self):
        return {"LLMTIER_ADMIN_TOKEN": "admin-secret", "LLMTIER_DATA_TOKEN": "data-secret"}

    def test_admin_first_on_shared_endpoint(self):
        env = self._env()
        usage_query = "/v1/usage?from=2000-01-01T00:00:00Z&to=2100-01-01T00:00:00Z"
        with patch.dict(os_environ(), env, clear=False):
            status_admin_get, admin_view, _ = self.request("GET", usage_query,
                                                           headers={"Authorization": "Bearer admin-secret"})
            status_data_get, data_view, _ = self.request("GET", usage_query,
                                                         headers={"Authorization": "Bearer data-secret"})
            status_admin_del, _, _ = self.request("DELETE", usage_query,
                                                  headers={"Authorization": "Bearer admin-secret"})
            status_data_del, del_data, _ = self.request("DELETE", usage_query,
                                                        headers={"Authorization": "Bearer data-secret"})
        self.assertEqual(200, status_admin_get)
        self.assertEqual(200, status_data_get)
        self.assertEqual(200, status_admin_del)
        self.assertEqual(403, status_data_del)
        self.assertEqual("permission_denied", del_data["error"]["code"])

    def test_unauthenticated_on_shared_endpoint_is_401_with_malformed_header(self):
        with patch.dict(os_environ(), self._env(), clear=False):
            status, payload, _ = self.request("GET", "/v1/usage?from=2000-01-01T00:00:00Z&to=2100-01-01T00:00:00Z",
                                              headers={"Authorization": "token xyz"})
        self.assertEqual(401, status)


def os_environ():
    import os
    return os.environ


if __name__ == "__main__":
    unittest.main()
