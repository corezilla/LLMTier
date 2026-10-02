"""MT-MGMT-010 — AccountUsage.refresh 四态分支（M004，层②/层③ K7，negative，P1）。

K7 组合行（provider × 凭据 × 确认）：(local, 无凭据, 已确认)→unlimited /
(minimax, 有凭据, 未确认)→400 / (minimax, 无凭据, 已确认)→unavailable /
(volc, 无凭据, 已确认)→unavailable；none→unsupported；未知 provider→404。
GET 路径不触网（K7 第一行的网络面证据归 MT-MGMT-005）。
"""
from __future__ import annotations

import unittest

from tests.module.cases.support.http_env import LoopbackEnv


class RefreshBranchTests(LoopbackEnv):
    def _create(self, name, usage):
        status, provider, _ = self.request("POST", "/v1/providers",
                                           body={"name": name, "kind": "local", "endpoint": "http://127.0.0.1:9",
                                                 "secret_ref": None, "enabled": True, "usage": usage})
        self.assertEqual(201, status)
        return provider

    def _refresh(self, provider_id, confirm=True):
        body = {"confirm_external_call": confirm}
        return self.request("POST", f"/v1/providers/{provider_id}/usage", body=body)

    def test_local_no_credentials_confirmed_is_unlimited(self):
        provider = self._create("k7-local", {"usage_provider": "local"})
        status, payload, _ = self._refresh(provider["id"])
        self.assertEqual((200, "unlimited"), (status, payload["status"]))

    def test_minimax_with_credentials_unconfirmed_is_400(self):
        provider = self._create("k7-minimax", {"usage_provider": "minimax", "usage_api_key_ref": "env:LLMTIER_K7_KEY"})
        status, payload, _ = self._refresh(provider["id"], confirm=False)
        self.assertEqual((400, "confirmation_required"), (status, payload["error"]["code"]))

    def test_minimax_without_credentials_confirmed_is_unavailable(self):
        provider = self._create("k7-minimax-nocred", {"usage_provider": "minimax"})
        status, payload, _ = self._refresh(provider["id"])
        self.assertEqual((200, "unavailable", "credentials_missing"), (status, payload["status"], payload["source"]))

    def test_volc_without_credentials_confirmed_is_unavailable(self):
        provider = self._create("k7-volc", {"usage_provider": "volc"})
        status, payload, _ = self._refresh(provider["id"])
        self.assertEqual((200, "unavailable", "credentials_missing"), (status, payload["status"], payload["source"]))
        self.assertEqual("volc_get_coding_plan_usage_requires_ak_sk", payload["error"])

    def test_none_provider_is_unsupported(self):
        provider = self._create("k7-none", {"usage_provider": "none"})
        status, payload, _ = self._refresh(provider["id"])
        self.assertEqual((200, "unsupported"), (status, payload["status"]))
        self.assertEqual("provider_usage_unsupported", payload["error"])

    def test_unknown_provider_is_404(self):
        status, payload, _ = self._refresh("px_missing")
        self.assertEqual((404, "not_found"), (status, payload["error"]["code"]))


if __name__ == "__main__":
    unittest.main()
