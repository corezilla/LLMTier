"""MT-OBS-001 — 组装后诊断端到端（M005 observability，层①，normal，P1）。

覆盖：一次真实 `POST /v1/responses` 之后，M001 诊断路由 → M006
`DiagnosticsService` 的**开关/快照/统计/trace/时间窗全链**同时生效。

环境：ENV-1 组装隔离库 + ENV-2 loopback HTTP（`PerTestLoopbackEnv`，每个
test 方法一份全新库与 loopback server，统计窗因此是单样本、百分位可精确
断言）；上游为 `_test_adapter` 边界替身（`FakeAdapter`，不触真实网络）。
时窗用 `2000-01-01T00:00:00Z` … `2999-01-01T00:00:00Z` 的冻结边界值。
"""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from tests.common.fakes import FakeAdapter
from tests.module.cases.support.http_env import PerTestLoopbackEnv

SINCE = "2000-01-01T00:00:00Z"
FUTURE = "2999-01-01T00:00:00Z"
PAST = "1999-01-01T00:00:00Z"
RESPONSE_BODY = {"model": "Worker", "input": "hi", "stream": True, "store": False}
SEEDED_ENDPOINT = "http://127.0.0.1:9"
SEEDED_BACKEND = "synthetic-chat"

SNAPSHOT_FIELDS = {"id", "request_id", "captured_at", "upstream_url", "backend_model", "http_status",
                   "latency_ms", "error_summary", "model", "deployment_id", "snapshot_type"}
WINDOW_FIELDS = {"stat_hour", "deployment_id", "model", "status_breakdown", "error_4xx_count",
                 "error_5xx_count", "request_count", "error_count", "latency_p50_ms", "latency_p95_ms",
                 "latency_min_ms", "latency_max_ms", "latency_sum_ms"}
USAGE_FIELDS = {"record_version", "is_final", "model", "input_tokens", "output_tokens",
                "total_tokens", "measurement_status", "source"}
CHAIN_STAGES = {"received", "validated", "routed", "upstream_started", "upstream_ended", "completed"}


class MTOBS001DiagnosticsEndToEnd(PerTestLoopbackEnv):
    """开关/快照/trace/统计/时间窗全链：经 M001 端点与 M006 服务组装后生效。"""

    def _deployment_id(self, tier="Worker"):
        return self.fx.app.registry.get_service_level(tier)[0]["deployment_ids"][0]

    def _enable(self, snapshots=True, stats=True):
        status, payload, _ = self.request("PATCH", "/v1/diagnostics",
                                          {"snapshots_enabled": snapshots, "stats_enabled": stats})
        self.assertEqual(200, status)
        return payload

    def _call(self, correlation=None):
        self.fx.app.responses._test_adapter = FakeAdapter(usage=True)
        try:
            headers = {"X-Correlation-ID": correlation} if correlation else None
            status, body, response_headers = self.request("POST", "/v1/responses", RESPONSE_BODY, headers)
        finally:
            self.fx.app.responses._test_adapter = None
        self.assertEqual(200, status)
        return response_headers["X-Request-ID"], body

    def _snapshot_of(self, request_id):
        status, payload, _ = self.request("GET", f"/v1/diagnostics/snapshots?since={SINCE}&until={FUTURE}")
        self.assertEqual(200, status)
        return next(item for item in payload["items"] if item["request_id"] == request_id)

    def _trace_of(self, request_id):
        status, payload, _ = self.request("GET", f"/v1/diagnostics/traces?since={SINCE}&until={FUTURE}")
        self.assertEqual(200, status)
        return next(item for item in payload["items"] if item["request_id"] == request_id)

    def _stats_of(self, since=SINCE, until=FUTURE):
        status, payload, _ = self.request("GET", f"/v1/diagnostics/stats?since={since}&until={until}")
        self.assertEqual(200, status)
        return {(w["stat_hour"], w["deployment_id"], w["model"]): w for w in payload["windows"]}

    def _hour(self):
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H")

    def test_diagnostic_routes_are_served_by_the_m001_handler(self):
        self._enable()
        status, switches, _ = self.request("GET", "/v1/diagnostics")
        self.assertEqual(200, status)
        self.assertEqual({"snapshots_enabled", "stats_enabled"}, set(switches))
        request_id, _ = self._call()
        for path in (f"/v1/diagnostics/snapshots?since={SINCE}&until={FUTURE}",
                     f"/v1/diagnostics/stats?since={SINCE}&until={FUTURE}",
                     f"/v1/diagnostics/traces?since={SINCE}&until={FUTURE}",
                     f"/v1/trace/{request_id}"):
            status, payload, _ = self.request("GET", path)
            self.assertEqual(200, status, path)
        self.assertEqual({"items", "next_cursor", "has_more"}, set(self.request("GET", "/v1/diagnostics/snapshots")[1]))
        self.assertEqual({"windows"}, set(self.request("GET", f"/v1/diagnostics/stats?since={SINCE}&until={FUTURE}")[1]))
        status, injections, _ = self.request("GET", f"/v1/deployments/{self._deployment_id()}/diagnostics")
        self.assertEqual(200, status)
        self.assertEqual([], injections)

    def test_snapshot_row_is_written_by_the_full_chain(self):
        self._enable()
        request_id, _ = self._call()
        snapshot = self._snapshot_of(request_id)
        self.assertEqual(SNAPSHOT_FIELDS, set(snapshot))
        self.assertTrue(snapshot["id"].startswith("snap_"))
        self.assertEqual(request_id, snapshot["request_id"])
        self.assertEqual(SEEDED_ENDPOINT, snapshot["upstream_url"])
        self.assertEqual(SEEDED_BACKEND, snapshot["backend_model"])
        self.assertEqual(200, snapshot["http_status"])
        self.assertIsNone(snapshot["error_summary"])
        self.assertEqual("Worker", snapshot["model"])
        self.assertEqual("upstream", snapshot["snapshot_type"])
        self.assertEqual(self._deployment_id(), snapshot["deployment_id"])
        self.assertGreater(snapshot["latency_ms"], 0)
        self.assertTrue(snapshot["captured_at"].endswith("Z"))

    def test_trace_stages_cover_the_chain_and_join_snapshot_and_usage(self):
        self._enable()
        request_id, _ = self._call("corr-obs-001")
        stages = {stage["stage"]: stage for stage in self._trace_of(request_id)["stages"]}
        self.assertEqual(CHAIN_STAGES, set(stages))
        self.assertEqual("corr-obs-001", stages["received"]["detail"]["x_correlation_id"])
        self.assertTrue(stages["received"]["detail"]["content_length"])
        self.assertEqual(True, stages["validated"]["detail"]["ok"])
        self.assertEqual(self._deployment_id(), stages["routed"]["detail"]["deployment_id"])
        self.assertIsNotNone(stages["routed"]["detail"]["provider_id"])
        self.assertEqual(SEEDED_ENDPOINT, stages["upstream_started"]["detail"]["upstream_url"])
        self.assertEqual(200, stages["upstream_ended"]["detail"]["status"])
        self.assertEqual(self._snapshot_of(request_id)["id"], stages["upstream_ended"]["detail"]["snapshot_id"])
        self.assertEqual(self._deployment_id(), stages["completed"]["detail"]["deployment_id"])
        # 只断言「按 stage_timestamp 升序返回」这一可观测契约：src 的 ORDER BY 兜底
        # 列是随机 uuid4，同毫秒阶段之间没有因果序保证（见报告 F-1）。
        ordered = [stage["timestamp"] for stage in self._trace_of(request_id)["stages"]]
        self.assertEqual(sorted(ordered), ordered)
        status, view, _ = self.request("GET", f"/v1/trace/{request_id}")
        self.assertEqual(200, status)
        self.assertEqual({"request_id", "correlation_id", "stages", "snapshot", "usage"}, set(view))
        self.assertEqual("corr-obs-001", view["correlation_id"])
        self.assertEqual(self._snapshot_of(request_id)["id"], view["snapshot"]["id"])
        self.assertEqual(USAGE_FIELDS, set(view["usage"]))
        self.assertEqual(True, view["usage"]["is_final"])
        self.assertEqual("measured", view["usage"]["measurement_status"])
        self.assertEqual((2, 1, 3), (view["usage"]["input_tokens"], view["usage"]["output_tokens"],
                                     view["usage"]["total_tokens"]))

    def test_time_window_excludes_rows_outside_the_window(self):
        self._enable()
        request_id, _ = self._call()
        self._snapshot_of(request_id)
        self.assertEqual([], self.request("GET", f"/v1/diagnostics/snapshots?since={FUTURE}&until={FUTURE}")[1]["items"])
        self.assertEqual([], self.request("GET", f"/v1/diagnostics/snapshots?since={SINCE}&until={PAST}")[1]["items"])
        self.assertEqual([], self.request("GET", f"/v1/diagnostics/traces?since={FUTURE}&until={FUTURE}")[1]["items"])
        self.assertEqual({}, self._stats_of(since=FUTURE, until=FUTURE))
        self.assertEqual({}, self._stats_of(since=PAST, until=PAST))
        # 统计窗按 UTC 小时桶归一（since/until 截断到 13 位），同一小时内仍命中
        hour_start = datetime.now(timezone.utc).replace(minute=30, second=0, microsecond=0).isoformat().replace("+00:00", "Z")
        self.assertIn((self._hour(), self._deployment_id(), "Worker"),
                      self._stats_of(since=hour_start, until=FUTURE))

    def test_stats_window_records_the_call(self):
        self._enable()
        self.assertEqual({}, self._stats_of())
        request_id, _ = self._call()
        self.assertEqual(200, self._snapshot_of(request_id)["http_status"])
        window = self._stats_of()[(self._hour(), self._deployment_id(), "Worker")]
        self.assertEqual(WINDOW_FIELDS, set(window))
        self.assertEqual({"200": 1}, window["status_breakdown"])
        self.assertEqual(1, window["request_count"])
        self.assertEqual(0, window["error_count"])
        self.assertEqual(0, window["error_4xx_count"])
        self.assertEqual(0, window["error_5xx_count"])
        self.assertEqual(window["latency_min_ms"], window["latency_max_ms"])
        self.assertEqual(window["latency_min_ms"], window["latency_sum_ms"])
        self.assertEqual(window["latency_min_ms"], window["latency_p50_ms"])
        self.assertEqual(window["latency_min_ms"], window["latency_p95_ms"])
        self.assertGreater(window["latency_min_ms"], 0)


if __name__ == "__main__":
    unittest.main()
