"""MT-OBS-003 — 诊断查询分支（M005 observability，层②，boundary，P1）。

覆盖：`/v1/diagnostics/{snapshots,stats,traces}` 与 `/v1/trace/{id}` 三个查询
面的字段完整性、`limit` 夹取边界与 cursor 分页；`upstream_url` 去 query
（`?token=` 不落库）；存储不可读→503 `usage_store_unavailable`（**不**伪装
空页）。

环境：ENV-1 组装隔离库 + ENV-2 loopback HTTP（`PerTestLoopbackEnv`：每个
test 方法一份全新库，存储面注入不会污染同文件的查询面用例）；上游为
`_test_adapter` 边界替身（`FakeAdapter`，不触真实网络）。

存储面注入（仅「存储不可读」用例，模块层 §1.5.1 存储面）两种形态：
(a) `os.chmod(db, 0o000)` —— 真实文件不可读，`sqlite3.connect` 直接失败
（`M001._run` 在 finally 关掉每请求的 thread-local 连接，故新请求必然重开）；
(b) `store.connection()` 上 `DROP TABLE` —— 表面不可用。两者都用来断言
M001 `_store_read` 的 503 出口与 M006 查询面的表现，不是伪造数据。
"""
from __future__ import annotations

import os
import stat
import unittest

from tests.common.fakes import FakeAdapter, response_capabilities
from tests.module.cases.support.http_env import PerTestLoopbackEnv

SINCE = "2000-01-01T00:00:00Z"
FUTURE = "2999-01-01T00:00:00Z"
SECRET = "TOKEN-SHOULD-NOT-PERSIST"
QUERY_ENDPOINT = f"https://api.example.com/v1?token={SECRET}&region=cn"
BASE_ENDPOINT = "https://api.example.com/v1"
RESPONSE_BODY = {"model": "Worker", "input": "hi", "stream": True, "store": False}
SNAPSHOT_FIELDS = {"id", "request_id", "captured_at", "upstream_url", "backend_model", "http_status",
                   "latency_ms", "error_summary", "model", "deployment_id", "snapshot_type"}
WINDOW_FIELDS = {"stat_hour", "deployment_id", "model", "status_breakdown", "error_4xx_count",
                 "error_5xx_count", "request_count", "error_count", "latency_p50_ms", "latency_p95_ms",
                 "latency_min_ms", "latency_max_ms", "latency_sum_ms"}
TRACE_VIEW_FIELDS = {"request_id", "correlation_id", "stages", "snapshot", "usage"}
DIAG_TABLES = ("trace_events", "diagnostic_snapshots", "data_plane_stats", "data_plane_latency_samples")


class MTOBS003DiagnosticsQueries(PerTestLoopbackEnv):
    """字段完整 / limit 夹取 / URL 去 query / 存储不可读 503。"""

    def _enable(self):
        status, payload, _ = self.request("PATCH", "/v1/diagnostics",
                                          {"snapshots_enabled": True, "stats_enabled": True})
        self.assertEqual(200, status)
        return payload

    def _call(self, model="Worker"):
        self.fx.app.responses._test_adapter = FakeAdapter(usage=True)
        try:
            status, _, headers = self.request("POST", "/v1/responses",
                                              {"model": model, "input": "hi", "stream": True, "store": False})
        finally:
            self.fx.app.responses._test_adapter = None
        self.assertEqual(200, status)
        return headers["X-Request-ID"]

    def _snapshots(self, query=""):
        status, payload, _ = self.request("GET", f"/v1/diagnostics/snapshots?since={SINCE}&until={FUTURE}{query}")
        self.assertEqual(200, status)
        return payload

    def _traces(self, query=""):
        status, payload, _ = self.request("GET", f"/v1/diagnostics/traces?since={SINCE}&until={FUTURE}{query}")
        self.assertEqual(200, status)
        return payload

    def _wire_query_endpoint_deployment(self):
        """经公开入口建带 query 的 endpoint 的 provider/deployment 并挂到 Senior。"""
        status, provider, _ = self.request("POST", "/v1/providers",
                                           {"name": "query-endpoint", "kind": "cloud",
                                            "endpoint": QUERY_ENDPOINT, "secret_ref": None, "enabled": True})
        self.assertEqual(201, status)
        status, deployment, _ = self.request("POST", "/v1/deployments",
                                             {"name": "query-deployment", "provider_id": provider["id"],
                                              "backend_model": "backend-x", "capabilities": response_capabilities(),
                                              "enabled": True})
        self.assertEqual(201, status)
        _, etag = self.fx.app.registry.get_service_level("Senior")
        status, _, _ = self.request("PATCH", "/v1/service-levels/Senior",
                                    {"deployment_ids": [deployment["id"]]}, {"If-Match": etag})
        self.assertEqual(200, status)
        # 夹具播种（与 AppFixture.seed / InferenceEnv._wire_cloud 同口径）：候选健康态置 healthy
        self.fx.app.store.connection().execute("UPDATE deployments SET health='healthy' WHERE id=?", (deployment["id"],))
        return deployment["id"]

    def _drop_diagnostics_tables(self):
        conn = self.fx.app.store.connection()
        for table in DIAG_TABLES:
            conn.execute(f"DROP TABLE {table}")

    def test_snapshot_item_carries_every_documented_field(self):
        self._enable()
        request_id = self._call()
        page = self._snapshots()
        self.assertEqual({"items", "next_cursor", "has_more"}, set(page))
        item = next(row for row in page["items"] if row["request_id"] == request_id)
        self.assertEqual(SNAPSHOT_FIELDS, set(item))
        self.assertEqual(200, item["http_status"])
        self.assertEqual("upstream", item["snapshot_type"])

    def test_stats_window_carries_every_documented_field(self):
        self._enable()
        self._call()
        status, payload, _ = self.request("GET", f"/v1/diagnostics/stats?since={SINCE}&until={FUTURE}")
        self.assertEqual(200, status)
        self.assertEqual({"windows"}, set(payload))
        self.assertNotEqual([], payload["windows"])
        self.assertEqual(WINDOW_FIELDS, set(payload["windows"][0]))

    def test_trace_view_carries_every_documented_field(self):
        self._enable()
        request_id = self._call()
        status, payload, _ = self.request("GET", f"/v1/trace/{request_id}")
        self.assertEqual(200, status)
        self.assertEqual(TRACE_VIEW_FIELDS, set(payload))
        for stage in payload["stages"]:
            self.assertEqual({"stage", "timestamp", "detail"}, set(stage))

    def test_limit_is_clamped_to_the_documented_range(self):
        self._enable()
        # 公开入口（M006 服务方法）播种 501 行，越界断言不依赖 HTTP 批量写入
        deployment_id = self.fx.app.registry.get_service_level("Worker")[0]["deployment_ids"][0]
        for index in range(501):
            self.fx.app.diagnostics.capture_snapshot(f"req_bulk_{index:04d}", deployment_id, "Worker",
                                                      "http://127.0.0.1:9", "synthetic-chat", 200, 1.0, None)
        # 下界：limit=0 → 1 行，has_more 为真
        low = self._snapshots("&limit=0")
        self.assertEqual(1, len(low["items"]))
        self.assertEqual(True, low["has_more"])
        self.assertEqual(low["items"][0]["id"], low["next_cursor"])
        # 上界：limit=99999 → 500 行（钳到 500）
        high = self._snapshots("&limit=99999")
        self.assertEqual(500, len(high["items"]))
        self.assertEqual(True, high["has_more"])
        # 走 cursor 翻到下一页，游标稳定
        second = self._snapshots(f"&limit=500&cursor={low['next_cursor']}")
        self.assertEqual(500, len(second["items"]))
        self.assertNotEqual([row["id"] for row in low["items"]], [row["id"] for row in second["items"]])

    def test_non_integer_limit_is_400(self):
        status, payload, _ = self.request("GET", "/v1/diagnostics/snapshots?limit=all")
        self.assertEqual(400, status)
        self.assertEqual("invalid_request", payload["error"]["code"])

    def test_stats_without_since_or_until_is_400(self):
        for query in ("", "?since=2000-01-01T00:00:00Z", "?until=2999-01-01T00:00:00Z"):
            status, payload, _ = self.request("GET", f"/v1/diagnostics/stats{query}")
            self.assertEqual(400, status, query)
            self.assertEqual("invalid_request", payload["error"]["code"])

    def test_snapshot_upstream_url_drops_the_query_string(self):
        self._enable()
        self._wire_query_endpoint_deployment()
        request_id = self._call("Senior")
        item = next(row for row in self._snapshots()["items"] if row["request_id"] == request_id)
        self.assertEqual(BASE_ENDPOINT, item["upstream_url"])

    def test_token_never_reaches_the_diagnostics_pages(self):
        self._enable()
        self._wire_query_endpoint_deployment()
        request_id = self._call("Senior")
        snapshots = self._snapshots()
        traces = self._traces()
        self.assertNotIn(SECRET, str(snapshots))
        self.assertNotIn(SECRET, str(traces))
        stage = next(s for row in traces["items"] if row["request_id"] == request_id
                     for s in row["stages"] if s["stage"] == "upstream_started")
        self.assertEqual(BASE_ENDPOINT, stage["detail"]["upstream_url"])
        status, view, _ = self.request("GET", f"/v1/trace/{request_id}")
        self.assertEqual(200, status)
        self.assertNotIn(SECRET, str(view))

    def test_dropped_diagnostics_tables_are_503_not_an_empty_page(self):
        self._enable()
        request_id = self._call()
        self.assertEqual(1, len(self.fx.app.diagnostics.snapshots_page(SINCE, FUTURE, None, None)["items"]))
        self._drop_diagnostics_tables()
        for path in (f"/v1/diagnostics/snapshots?since={SINCE}&until={FUTURE}",
                     f"/v1/diagnostics/stats?since={SINCE}&until={FUTURE}",
                     f"/v1/diagnostics/traces?since={SINCE}&until={FUTURE}",
                     f"/v1/trace/{request_id}"):
            status, payload, _ = self.request("GET", path)
            self.assertEqual(503, status, path)
            self.assertEqual("usage_store_unavailable", payload["error"]["code"])
            self.assertEqual("server_error", payload["error"]["type"])
            self.assertNotIn("items", payload)
            self.assertNotIn("windows", payload)
        # 开关表未受影响 → 开关面仍可读（说明 503 只来自查询面存储失败）
        status, payload, _ = self.request("GET", "/v1/diagnostics")
        self.assertEqual(200, status)
        self.assertEqual({"snapshots_enabled": True, "stats_enabled": True}, payload)

    def test_unreadable_database_file_is_503_not_an_empty_page(self):
        self._enable()
        request_id = self._call()
        baseline = self._snapshots()
        self.assertEqual(1, len(baseline["items"]))
        path = self.fx.app.store.path
        mode = stat.S_IMODE(os.stat(path).st_mode)
        self.fx.app.store.close()
        os.chmod(path, 0o000)
        try:
            for target in (f"/v1/diagnostics/snapshots?since={SINCE}&until={FUTURE}",
                           f"/v1/diagnostics/stats?since={SINCE}&until={FUTURE}",
                           f"/v1/diagnostics/traces?since={SINCE}&until={FUTURE}",
                           f"/v1/trace/{request_id}",
                           "/v1/diagnostics",
                           f"/tier/admin/v1/diagnostics/snapshots?since={SINCE}&until={FUTURE}"):
                status, payload, _ = self.request("GET", target)
                self.assertEqual(503, status, target)
                self.assertEqual("usage_store_unavailable", payload["error"]["code"], target)
                self.assertNotIn("items", payload, target)
                self.assertNotIn("windows", payload, target)
        finally:
            os.chmod(path, mode)
            self.fx.app.store.close()
        # 权限恢复后同一端点回到 200，且行未丢失 → 503 来自存储面而非数据为空
        self.assertEqual(baseline, self._snapshots())


if __name__ == "__main__":
    unittest.main()
