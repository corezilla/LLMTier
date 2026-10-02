"""MT-OBS-004 — 诊断注入分支与观测 fail-open（M005 observability，层②，recovery，P1）。

覆盖：`PATCH /v1/deployments/{id}/diagnostics` 经 M001 路由 → M006
`InjectionDiagnostics` 的四个分支——合法注入命中推理、非法类型 400、
非法 config 400、未知 deployment 404；以及观测库写失败时推理不变
（fail-open，`record_trace`/`capture_snapshot`/`record_latency` 各自吞错）。

环境：ENV-1 组装隔离库 + ENV-2 loopback HTTP（`PerTestLoopbackEnv`：每个
test 方法一份全新库，存储面注入不会污染同文件的注入分支用例）；上游为
`_test_adapter` 边界替身（`FakeAdapter`，不触真实网络）。

存储面注入（仅 fail-open 用例，模块层 §1.5.1 存储面）：对
`store.connection()` 执行 `DROP TABLE` 制造真实写失败，断言
`DiagnosticsService` 的 fail-open 契约与 M004 账本的 measured 终态。
"""
from __future__ import annotations

import unittest

from tests.common.fakes import FakeAdapter
from tests.module.cases.support.http_env import PerTestLoopbackEnv

SINCE = "2000-01-01T00:00:00Z"
FUTURE = "2999-01-01T00:00:00Z"
RESPONSE_BODY = {"model": "Worker", "input": "hi", "stream": True, "store": False}
DIAG_TABLES = ("trace_events", "diagnostic_snapshots", "data_plane_stats", "data_plane_latency_samples")
INJECTION_ITEM_FIELDS = {"id", "deployment_id", "type", "config", "enabled", "updated_at"}


class MTOBS004DiagnosticsInjection(PerTestLoopbackEnv):
    """注入三分支（合法命中 / 非法 400 / 未知 deployment 404）+ 观测 fail-open。"""

    def _deployment_id(self):
        return self.fx.app.registry.get_service_level("Worker")[0]["deployment_ids"][0]

    def _set(self, items, deployment_id=None):
        return self.request("PATCH", f"/v1/deployments/{deployment_id or self._deployment_id()}/diagnostics",
                            {"items": items})

    def _call(self):
        self.fx.app.responses._test_adapter = FakeAdapter(usage=True)
        try:
            return self.request("POST", "/v1/responses", RESPONSE_BODY)
        finally:
            self.fx.app.responses._test_adapter = None

    def _usage_rows(self):
        return self.fx.app.usage.page("loopback-consumer", None, 200, admin=True,
                                      since=SINCE, until=FUTURE)["data"]

    def _injection_audits(self):
        return [row for row in self.fx.app.audit.page(limit=200)["data"]
                if row["action"] == "diagnostics.injection.update"]

    def _audit_of(self, headers):
        """审计行按 `X-Request-ID` 归位（M001 每个请求一个 request_id）。"""
        rows = [row for row in self._injection_audits() if row["request_id"] == headers.get("X-Request-ID")]
        self.assertEqual(1, len(rows))
        return rows[0]

    def test_legal_injection_is_persisted_and_hits_inference(self):
        deployment_id = self._deployment_id()
        status, payload, headers = self._set([{"type": "fault_502", "config": {"error_body": "injected boom"},
                                               "enabled": True}])
        self.assertEqual(200, status)
        self.assertEqual(1, len(payload))
        item = payload[0]
        self.assertEqual(INJECTION_ITEM_FIELDS, set(item))
        self.assertEqual("fault_502", item["type"])
        self.assertEqual({"error_body": "injected boom"}, item["config"])
        self.assertEqual(True, item["enabled"])
        self.assertEqual(deployment_id, item["deployment_id"])
        # GET 面回读同一行
        status, listed, _ = self.request("GET", f"/v1/deployments/{deployment_id}/diagnostics")
        self.assertEqual(200, status)
        self.assertEqual([item["id"]], [row["id"] for row in listed])
        self.assertEqual("success", self._audit_of(headers)["result"])
        # 注入命中：注入体作为上游失败返回，且账本以 injected 收敛
        status, error, _ = self._call()
        self.assertEqual(502, status)
        self.assertEqual("provider_failure", error["error"]["code"])
        self.assertEqual("injected boom", error["error"]["message"])
        self.assertEqual(True, error["error"]["retryable"])
        rows = self._usage_rows()
        self.assertEqual("injected", rows[-1]["source"])
        self.assertEqual("unknown", rows[-1]["measurement_status"])
        self.assertIsNone(rows[-1]["total_tokens"])

    def test_unknown_injection_type_is_400_invalid_injection(self):
        status, payload, headers = self._set([{"type": "meltdown", "config": {}, "enabled": True}])
        self.assertEqual(400, status)
        self.assertEqual("invalid_injection", payload["error"]["code"])
        self.assertEqual("type", payload["error"]["param"])
        # 校验在 M006 内、M004 mutate 的事务里 → 审计行记 failed
        self.assertEqual("failed", self._audit_of(headers)["result"])
        self.assertEqual([], self.request("GET", f"/v1/deployments/{self._deployment_id()}/diagnostics")[1])

    def test_missing_injection_config_field_is_400_invalid_injection(self):
        for item, param in (({"type": "delay", "config": {}, "enabled": True}, "delay_ms"),
                            ({"type": "fault_503", "config": {}, "enabled": True}, "error_body"),
                            ({"type": "delay", "config": {"delay_ms": 5}, "enabled": "yes"}, "enabled"),
                            ({"type": "delay", "config": {"delay_ms": 60001}, "enabled": True}, "delay_ms")):
            status, payload, _ = self._set([item])
            self.assertEqual(400, status, item)
            self.assertEqual("invalid_injection", payload["error"]["code"])
            self.assertEqual(param, payload["error"]["param"])
        self.assertEqual([], self.request("GET", f"/v1/deployments/{self._deployment_id()}/diagnostics")[1])

    def test_unknown_deployment_is_404_on_both_verbs(self):
        # GET 是读路径：404 且不落审计行
        status, payload, headers = self.request("GET", "/v1/deployments/does-not-exist/diagnostics")
        self.assertEqual(404, status)
        self.assertEqual("not_found", payload["error"]["code"])
        self.assertEqual([], [row for row in self._injection_audits()
                              if row["request_id"] == headers.get("X-Request-ID")])
        # PATCH 走 M004 mutate：404 且审计行记 failed
        status, payload, headers = self._set([{"type": "delay", "config": {"delay_ms": 5}, "enabled": True}],
                                            deployment_id="does-not-exist")
        self.assertEqual(404, status)
        self.assertEqual("not_found", payload["error"]["code"])
        audit = self._audit_of(headers)
        self.assertEqual("failed", audit["result"])
        self.assertEqual("does-not-exist", audit["target"])

    def test_patch_without_items_is_400(self):
        status, payload, headers = self.request("PATCH", f"/v1/deployments/{self._deployment_id()}/diagnostics", {})
        self.assertEqual(400, status)
        self.assertEqual("invalid_request", payload["error"]["code"])
        # 形状校验在 M001，禁入 M004 mutate → 该请求不落审计行
        self.assertEqual([], [row for row in self._injection_audits()
                              if row["request_id"] == headers.get("X-Request-ID")])

    def test_empty_items_revokes_every_injection(self):
        deployment_id = self._deployment_id()
        self._set([{"type": "fault_502", "config": {"error_body": "boom"}, "enabled": True}])
        self._set([{"type": "delay", "config": {"delay_ms": 1}, "enabled": True}])
        self.assertEqual(2, len(self.request("GET", f"/v1/deployments/{deployment_id}/diagnostics")[1]))
        status, payload, _ = self._set([])
        self.assertEqual(200, status)
        self.assertEqual([], payload)
        self.assertEqual([], self.request("GET", f"/v1/deployments/{deployment_id}/diagnostics")[1])
        status, _, _ = self._call()
        self.assertEqual(200, status)

    def test_inference_is_unchanged_when_every_observability_write_fails(self):
        status, _, _ = self.request("PATCH", "/v1/diagnostics",
                                    {"snapshots_enabled": True, "stats_enabled": True})
        self.assertEqual(200, status)
        healthy_status, healthy_body, healthy_headers = self._call()
        self.assertEqual(200, healthy_status)
        conn = self.fx.app.store.connection()
        for table in DIAG_TABLES:
            conn.execute(f"DROP TABLE {table}")
        status, body, _ = self._call()
        # 推理结果不变（字节级等同；request_id 是唯一允许的差异来源）
        self.assertEqual(200, status)
        self.assertEqual(b"response.created" in body, b"response.created" in healthy_body)
        self.assertEqual(b"event: response.completed" in body, b"event: response.completed" in healthy_body)
        self.assertIn(b"data: [DONE]", body)
        self.assertIn(b'"total_tokens":3', body)
        self.assertIsNotNone(healthy_headers["X-Request-ID"])
        # 账本终态不受影响：measured + provider + 真实 token
        rows = self._usage_rows()
        self.assertEqual(2, len(rows))
        for row in rows:
            self.assertEqual(True, row["is_final"])
            self.assertEqual("measured", row["measurement_status"])
            self.assertEqual("provider", row["source"])
            self.assertEqual((2, 1, 3), (row["input_tokens"], row["output_tokens"], row["total_tokens"]))
        # fail-open 证据：三个写入面各自被记为 warning
        page = self.fx.app.logs.page(since=SINCE, until=FUTURE)
        warnings = [row for row in page["data"] if row["event"] == "capture_failed"]
        self.assertTrue(warnings)
        self.assertEqual({"warning"}, {row["level"] for row in warnings})
        self.assertEqual({"diagnostics"}, {row["module"] for row in warnings})
        self.assertTrue(any("trace write failed" in row["message"] for row in warnings))
        self.assertTrue(any("snapshot write failed" in row["message"] for row in warnings))
        self.assertTrue(any("stats write failed" in row["message"] for row in warnings))
        # 查询面 503（读失败不静默为空页）
        status, payload, _ = self.request("GET", f"/v1/diagnostics/snapshots?since={SINCE}&until={FUTURE}")
        self.assertEqual(503, status)
        self.assertEqual("usage_store_unavailable", payload["error"]["code"])


if __name__ == "__main__":
    unittest.main()
