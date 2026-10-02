"""MT-MGMT-005 — AccountUsage 组装后账号用量（M004，层①，negative，P1）。

GET 不触网（not_refreshed 快照、上游命中 0）；未确认 POST→400；凭据缺失→
`unavailable`+error；provider 报错→`unavailable`+error 且快照持久。
minimax URL 经模块常量重指至 loopback 假上游（边界替身，不触真实外网）。

另覆盖 `admin.mutate(atomic=False)` 审计例外：account usage refresh 走
`atomic=False` 路径（业务外部调用不占业务事务），成功与失败均须留审计行，
失败时业务无半写（`admin.py::mutate`）。
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from management import account_usage
from tests.module.cases.support.http_env import LoopbackEnv
from tests.module.cases.support.upstream import FakeUpstream


class AccountUsageTests(LoopbackEnv):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.upstream = FakeUpstream(mode="minimax_error")
        cls._minimax_patcher = patch.object(account_usage, "MINIMAX_USAGE_URL",
                                            f"{cls.upstream.endpoint}/v1/token_plan/remains")
        cls._minimax_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls._minimax_patcher.stop()
        cls.upstream.stop()
        super().tearDownClass()

    def _create(self, name, usage):
        status, provider, _ = self.request("POST", "/v1/providers",
                                           body={"name": name, "kind": "local", "endpoint": "http://127.0.0.1:9",
                                                 "secret_ref": None, "enabled": True, "usage": usage})
        self.assertEqual(201, status)
        return provider

    def _latest(self, provider_id):
        return self.request("GET", f"/v1/providers/{provider_id}/usage")

    def _refresh(self, provider_id, confirm=True):
        # confirm=False → 显式 false（空体会先被 body 形状校验拦成 invalid_request）
        return self.request("POST", f"/v1/providers/{provider_id}/usage",
                            body={"confirm_external_call": confirm})

    def test_get_does_not_touch_network(self):
        provider = self._create("usage-none", {"usage_provider": "none"})
        hits_before = self.upstream.hits()
        status, payload, _ = self._latest(provider["id"])
        self.assertEqual(200, status)
        self.assertEqual("not_refreshed", payload["status"])
        self.assertEqual(hits_before, self.upstream.hits())

    def test_refresh_without_confirm_is_400(self):
        provider = self._create("usage-noconf", {"usage_provider": "none"})
        status, payload, _ = self._refresh(provider["id"], confirm=False)
        self.assertEqual(400, status)
        self.assertEqual("confirmation_required", payload["error"]["code"])

    def test_minimax_missing_credentials_is_unavailable(self):
        provider = self._create("usage-minimax-nocred", {"usage_provider": "minimax"})
        status, payload, _ = self._refresh(provider["id"])
        self.assertEqual(200, status)
        self.assertEqual("unavailable", payload["status"])
        self.assertEqual("credentials_missing", payload["source"])
        status, latest, _ = self._latest(provider["id"])
        self.assertEqual("unavailable", latest["status"])

    def test_provider_error_is_unavailable_and_persisted(self):
        provider = self._create("usage-minimax-err",
                                {"usage_provider": "minimax", "usage_api_key_ref": "env:LLMTIER_MINIMAX_TEST_KEY"})
        import os
        os.environ["LLMTIER_MINIMAX_TEST_KEY"] = "k-test"
        try:
            hits_before = self.upstream.hits()
            status, payload, _ = self._refresh(provider["id"])
            self.assertEqual(200, status)
            self.assertEqual("unavailable", payload["status"])
            self.assertEqual("provider_api_error", payload["source"])
            self.assertTrue(payload["error"])
            self.assertEqual(hits_before + 1, self.upstream.hits())
        finally:
            os.environ.pop("LLMTIER_MINIMAX_TEST_KEY", None)
        # 快照持久：GET 返回错误快照
        status, latest, _ = self._latest(provider["id"])
        self.assertEqual("unavailable", latest["status"])
        self.assertEqual("provider_api_error", latest["source"])

    def test_local_provider_is_unlimited(self):
        provider = self._create("usage-local", {"usage_provider": "local"})
        status, payload, _ = self._refresh(provider["id"])
        self.assertEqual(200, status)
        self.assertEqual("unlimited", payload["status"])

    def _audits(self, action="provider.usage.refresh"):
        _, page, _ = self.request("GET", "/v1/audit?limit=200")
        return [r for r in page["data"] if r["action"] == action]

    def test_non_atomic_refresh_success_is_audited(self):
        provider = self._create("usage-nonatomic-ok", {"usage_provider": "local"})
        status, payload, _ = self._refresh(provider["id"])
        self.assertEqual(200, status)
        rows = [r for r in self._audits() if r["target"] == provider["id"] and r["result"] == "success"]
        self.assertTrue(rows)

    def test_non_atomic_refresh_failure_is_audited_and_writes_nothing(self):
        # 未知 provider：refresh 抛 404（业务未写），mutate 的 except 仍留 failed 审计行
        status, payload, _ = self._refresh("provider_missing")
        self.assertEqual(404, status)
        self.assertEqual("not_found", payload["error"]["code"])
        failed = [r for r in self._audits() if r["target"] == "provider_missing" and r["result"] == "failed"]
        self.assertTrue(failed)
        self.assertTrue(all(r["request_id"] for r in failed))
        # 业务无半写：未知 provider 不留任何账号用量快照
        snapshots = self.fx.app.store.all("SELECT * FROM provider_usage_snapshots WHERE provider_id=?", ("provider_missing",))
        self.assertEqual([], snapshots)


if __name__ == "__main__":
    unittest.main()
