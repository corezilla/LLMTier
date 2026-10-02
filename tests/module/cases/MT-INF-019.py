"""MT-INF-019 — provider 凭据解析分支（M003，层②，negative，P1；§1.5.1 a24/b8）。

`secret_ref` 为 `file:` 不可读 → 503 `provider_secret_unavailable`（不 dispatch、
无上游命中）；`env:` 空值 → 按 `src/` 语义静默无 Authorization 头发出请求
（可观测于 loopback 上游）。
"""
from __future__ import annotations

import unittest

from http_api.errors import ApiError
from tests.module.cases.support.inference_env import RESPONSE_BODY, InferenceEnv


class SecretRefTests(InferenceEnv):
    def _repoint_secret(self, secret_ref):
        provider_id = self.senior["provider_id"] if hasattr(self.senior, "provider_id") else None
        # 经公开入口查询 provider id
        providers = self.fx.app.registry.list_providers()
        cloud = next(p for p in providers if p["name"] == "cloud-Senior")
        view, etag = self.fx.app.registry.get_provider(cloud["id"])
        return self.fx.app.registry.update_provider(cloud["id"], {"secret_ref": secret_ref}, etag)

    def _hits(self):
        return self.upstream.hits()

    def _auth_headers_seen(self):
        auths = [headers.get("Authorization") for _, path, headers in self.upstream.requests]
        return auths

    def test_unreadable_secret_file_is_503_no_dispatch(self):
        self._repoint_secret("file:/nonexistent/secret/path")
        hits_before = self._hits()
        with self.assertRaises(ApiError) as cm:
            self.fx.app.responses.create("consumer", "req_secret_file", RESPONSE_BODY)
        self.assertEqual(("provider_secret_unavailable", 503), (cm.exception.code, cm.exception.status))
        self.assertEqual(hits_before, self._hits())
        row = self.head_record("req_secret_file")
        self.assertEqual("unknown", row["measurement_status"])

    def test_empty_env_secret_sends_request_without_authorization(self):
        self._repoint_secret("env:LLMTIER_DEFINITELY_UNSET_VAR_XYZ")
        result = self.fx.app.responses.create("consumer", "req_secret_env", RESPONSE_BODY)
        self.assertEqual("completed", result["status"])
        self.assertEqual(1, self._hits())
        auths = self._auth_headers_seen()
        self.assertTrue(all(a is None for a in auths))

    def test_env_secret_value_is_sent_as_bearer(self):
        import os
        os.environ["LLMTIER_TEST_SECRET"] = "sk-test-123"
        try:
            self._repoint_secret("env:LLMTIER_TEST_SECRET")
            self.upstream.requests.clear()
            self.fx.app.responses.create("consumer", "req_secret_env2", RESPONSE_BODY)
            auths = self._auth_headers_seen()
            self.assertTrue(any(a == "Bearer sk-test-123" for a in auths))
        finally:
            os.environ.pop("LLMTIER_TEST_SECRET", None)

    def test_ledger_unknown_on_secret_failure(self):
        self._repoint_secret("file:/nonexistent/secret/path2")
        with self.assertRaises(ApiError):
            self.fx.app.responses.create("consumer", "req_secret_file2", RESPONSE_BODY)
        row = self.head_record("req_secret_file2")
        self.assertTrue(row["is_final"])
        self.assertEqual("unknown", row["measurement_status"])


if __name__ == "__main__":
    unittest.main()
