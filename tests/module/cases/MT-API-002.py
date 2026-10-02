"""MT-API-002 — 契约别名 /tier/admin/v1/* 与 /v1/* 端到端 parity（M001，层①，normal，P1）。

组装保证：别名与扁平命名空间走同一路由→服务→存储路径，资源视图逐字节一致。
（别名集合以 `src/http_api/app.py` 实际注册为准：diagnostics 开关/快照/统计/traces、
deployment 注入、单请求 trace。）
"""
from __future__ import annotations

import unittest

from tests.module.cases.support.http_env import LoopbackEnv


class AliasParityTests(LoopbackEnv):
    def test_diagnostics_switches_parity(self):
        _, flat, _ = self.request("GET", "/v1/diagnostics")
        _, alias, _ = self.request("GET", "/tier/admin/v1/diagnostics")
        self.assertEqual(flat, alias)
        status_a, patched, _ = self.request("PATCH", "/v1/diagnostics", body={"snapshots_enabled": True})
        status_b, alias_patched, _ = self.request("PATCH", "/tier/admin/v1/diagnostics", body={"stats_enabled": True})
        self.assertEqual(200, status_a); self.assertEqual(200, status_b)
        _, flat2, _ = self.request("GET", "/v1/diagnostics")
        self.assertEqual({"snapshots_enabled": True, "stats_enabled": True}, flat2)
        _, alias2, _ = self.request("GET", "/tier/admin/v1/diagnostics")
        self.assertEqual(flat2, alias2)

    def test_deployment_injections_parity(self):
        provider, deployment = _seeded(self)
        items = [{"type": "delay", "enabled": True, "config": {"delay_ms": 1}}]
        status, via_flat, _ = self.request("PATCH", f"/v1/deployments/{deployment['id']}/diagnostics", body={"items": items})
        status2, via_alias, _ = self.request("PATCH", f"/tier/admin/v1/deployments/{deployment['id']}/diagnostics",
                                             body={"items": [{"type": "rate_limit", "enabled": True, "config": {"retry_after_sec": 1}}]})
        self.assertEqual(200, status); self.assertEqual(200, status2)
        _, flat_list, _ = self.request("GET", f"/v1/deployments/{deployment['id']}/diagnostics")
        _, alias_list, _ = self.request("GET", f"/tier/admin/v1/deployments/{deployment['id']}/diagnostics")
        self.assertEqual(flat_list, alias_list)
        self.assertEqual({"delay", "rate_limit"}, {i["type"] for i in alias_list})

    def test_traces_and_trace_parity(self):
        provider, deployment = _seeded(self)
        _, flat, _ = self.request("GET", "/v1/diagnostics/traces?since=2000-01-01T00:00:00Z&until=2100-01-01T00:00:00Z")
        _, alias, _ = self.request("GET", "/tier/admin/v1/diagnostics/traces?since=2000-01-01T00:00:00Z&until=2100-01-01T00:00:00Z")
        self.assertEqual(flat, alias)
        _, flat_stats, _ = self.request("GET", "/v1/diagnostics/stats?since=2000-01-01T00:00:00Z&until=2100-01-01T00:00:00Z")
        _, alias_stats, _ = self.request("GET", "/tier/admin/v1/diagnostics/stats?since=2000-01-01T00:00:00Z&until=2100-01-01T00:00:00Z")
        self.assertEqual(flat_stats, alias_stats)
        _, flat_snaps, _ = self.request("GET", "/v1/diagnostics/snapshots?since=2000-01-01T00:00:00Z&until=2100-01-01T00:00:00Z")
        _, alias_snaps, _ = self.request("GET", "/tier/admin/v1/diagnostics/snapshots?since=2000-01-01T00:00:00Z&until=2100-01-01T00:00:00Z")
        self.assertEqual(flat_snaps, alias_snaps)

    def test_alias_unknown_deployment_parity_404(self):
        for base in ("/v1", "/tier/admin/v1"):
            status, payload, _ = self.request("GET", f"{base}/deployments/dep_missing/diagnostics")
            self.assertEqual(404, status)
            self.assertEqual("not_found", payload["error"]["code"])


def _seeded(test):
    providers = test.request("GET", "/v1/providers")[1]["data"]
    assert providers, "seeded provider missing"
    deployments = test.request("GET", "/v1/deployments")[1]["data"]
    return providers[0], deployments[0]


def _deployment_id(test):
    return _seeded(test)[1]["id"]


if __name__ == "__main__":
    unittest.main()
