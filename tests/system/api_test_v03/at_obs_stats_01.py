"""Case ID: OBS-STATS-01

Endpoint: GET /v1/diagnostics/stats?since=...&until=...
Upstream Provider: 无（仅诊断读面；不触上游）
Model: 无
Auth: Bearer dev-admin

TS-002 依赖：
  Endpoint: http://192.168.1.9:8181（m5air 已部署实例）
  上游: 无（本 case 不触上游）
  模型: 无

TS-003：不触上游，无 provider endpoint。

目标：GET /v1/diagnostics/stats 返回按小时桶聚合的 StatsView：顶层恰 {windows}，
每窗口为恰好 13 键的 StatsWindow。空 windows 合法（fail-open）。
"""
from __future__ import annotations

import re

import pytest

STATS_PATH = "/v1/diagnostics/stats"
WINDOW = {"since": "2000-01-01T00:00:00Z", "until": "2100-01-01T00:00:00Z"}
STAT_HOUR_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}$")
WINDOW_KEYS = {
    "stat_hour", "deployment_id", "model", "status_breakdown",
    "error_4xx_count", "error_5xx_count", "request_count", "error_count",
    "latency_p50_ms", "latency_p95_ms", "latency_min_ms", "latency_max_ms",
    "latency_sum_ms",
}


@pytest.mark.api_a
def test_obs_stats_01_windows_shape(admin_client):
    resp = admin_client.get(STATS_PATH, params=WINDOW)
    assert resp.status_code == 200, (
        f"期望 200，实际 {resp.status_code}: {resp.text}"
    )
    assert "application/json" in resp.headers.get("content-type", ""), (
        f"Content-Type 非 JSON: {resp.headers.get('content-type')}"
    )
    body = resp.json()
    assert set(body.keys()) == {"windows"}, (
        f"StatsView 顶层键集应恰为 {{windows}}: {sorted(body.keys())}"
    )
    assert isinstance(body["windows"], list), f"windows 应为数组: {body['windows']!r}"

    for window in body["windows"]:
        assert set(window.keys()) == WINDOW_KEYS, (
            f"StatsWindow 键集应恰为 13 键: {sorted(window.keys())}"
        )
        assert STAT_HOUR_RE.match(window["stat_hour"]), (
            f"stat_hour 形状不符（小时桶）: {window['stat_hour']!r}"
        )
        for key in ("deployment_id", "model"):
            assert window[key] is None or isinstance(window[key], str), (
                f"{key} 应为字符串或 null: {window[key]!r}"
            )
        assert isinstance(window["status_breakdown"], dict), (
            f"status_breakdown 应为对象: {window['status_breakdown']!r}"
        )
        for count in window["status_breakdown"].values():
            assert isinstance(count, int) and count >= 0, (
                f"status_breakdown 值应为非负整数: {count!r}"
            )
        for key in ("error_4xx_count", "error_5xx_count", "request_count", "error_count"):
            assert isinstance(window[key], int) and not isinstance(window[key], bool) and window[key] >= 0, (
                f"{key} 应为非负整数: {window[key]!r}"
            )
        for key in ("latency_p50_ms", "latency_p95_ms", "latency_min_ms", "latency_max_ms"):
            assert window[key] is None or isinstance(window[key], (int, float)), (
                f"{key} 应为 null 或数值: {window[key]!r}"
            )
        assert isinstance(window["latency_sum_ms"], (int, float)) and not isinstance(window["latency_sum_ms"], bool), (
            f"latency_sum_ms 应为数值: {window['latency_sum_ms']!r}"
        )
        assert window["latency_sum_ms"] >= 0, f"latency_sum_ms 应 >=0: {window['latency_sum_ms']!r}"

    filtered = admin_client.get(
        STATS_PATH, params={**WINDOW, "deployment_id": "dep_omlx_qwen36"}
    )
    assert filtered.status_code == 200, (
        f"过滤请求期望 200，实际 {filtered.status_code}: {filtered.text}"
    )
    for window in filtered.json()["windows"]:
        assert window["deployment_id"] == "dep_omlx_qwen36", (
            f"过滤窗口 deployment_id 不符: {window['deployment_id']!r}"
        )
