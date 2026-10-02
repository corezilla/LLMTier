"""MT-MGMT-014 — `/v1/stats` 组装链（M004 组装，层①，negative，P1）。

组装保证：`GET /v1/stats` 的组装层（`app.py`）对 `from`/`to` 必填做 400
`invalid_request` 校验（UT 直接调 `admin.stats` 不经此分支）；`group_by=tier`
与 `group_by=deployment` 两分组返回正确形状与分组键；`group_by` 非法→400
（由 `admin.stats` 的 `require` 抛，app 层只做 `.lower()` 归一）。

环境：ENV-1 组装隔离库 + ENV-2 loopback HTTP（`PerTestLoopbackEnv`：每方法一份
新库）。用量经公开入口 `POST /v1/responses` 造数，适配器为 `_test_adapter`
边界替身（`FakeAdapter`，不触网络）；分组断言以真实 `usage_*` 表聚合为准。
"""
from __future__ import annotations

import unittest

from tests.common.fakes import FakeAdapter
from tests.module.cases.support.http_env import PerTestLoopbackEnv

SINCE = "2000-01-01T00:00:00Z"
FUTURE = "2100-01-01T00:00:00Z"
RESPONSE_BODY = {"model": "Worker", "input": "hi", "stream": True, "store": False}
TIER_KEYS = {"tier", "calls", "measured_calls", "unknown_calls", "input_tokens", "output_tokens",
             "total_tokens", "cached_tokens", "cache_write_tokens", "reasoning_tokens"}
DEPLOYMENT_KEYS = {"deployment_id", "deployment_name", "backend_model", "provider_id", "provider_name",
                   "provider_kind", "calls", "measured_calls", "unknown_calls", "input_tokens",
                   "output_tokens", "total_tokens", "cached_tokens", "cache_write_tokens", "reasoning_tokens"}


class StatsTests(PerTestLoopbackEnv):
    def _call(self, request_id):
        self.fx.app.responses._test_adapter = FakeAdapter(usage=True)
        try:
            status, _, _ = self.request("POST", "/v1/responses", RESPONSE_BODY)
        finally:
            self.fx.app.responses._test_adapter = None
        self.assertEqual(200, status)
        return request_id

    def _stats(self, group_by=None, since=SINCE, until=FUTURE):
        query = f"?from={since}&to={until}"
        if group_by is not None:
            query += f"&group_by={group_by}"
        return self.request("GET", f"/v1/stats{query}")

    def test_missing_from_or_to_is_400(self):
        for query in ("", f"?to={FUTURE}", f"?from={SINCE}"):
            status, payload, _ = self.request("GET", f"/v1/stats{query}")
            self.assertEqual(400, status, query)
            self.assertEqual("invalid_request", payload["error"]["code"])

    def test_group_by_tier_structure_and_keys(self):
        self._call("req_stats_tier")
        status, payload, _ = self._stats("tier")
        self.assertEqual(200, status)
        self.assertEqual(SINCE, payload["from"])
        self.assertEqual(FUTURE, payload["to"])
        self.assertEqual("tier", payload["group_by"])
        self.assertEqual(1, len(payload["data"]))
        row = payload["data"][0]
        self.assertEqual(TIER_KEYS, set(row))
        self.assertEqual("Worker", row["tier"])
        self.assertEqual(1, row["calls"])
        self.assertEqual(1, row["measured_calls"])

    def test_group_by_deployment_structure_and_keys(self):
        self._call("req_stats_dep")
        status, payload, _ = self._stats("deployment")
        self.assertEqual(200, status)
        self.assertEqual("deployment", payload["group_by"])
        self.assertEqual(1, len(payload["data"]))
        row = payload["data"][0]
        self.assertEqual(DEPLOYMENT_KEYS, set(row))
        self.assertEqual(1, row["calls"])
        self.assertEqual(1, row["measured_calls"])
        self.assertEqual("synthetic-chat", row["backend_model"])
        self.assertEqual("local", row["provider_kind"])

    def test_group_by_defaults_to_tier(self):
        self._call("req_stats_default")
        status, payload, _ = self._stats(None)
        self.assertEqual(200, status)
        self.assertEqual("tier", payload["group_by"])

    def test_invalid_group_by_is_400(self):
        status, payload, _ = self._stats("bogus")
        self.assertEqual(400, status)
        self.assertEqual("invalid_request", payload["error"]["code"])


if __name__ == "__main__":
    unittest.main()
