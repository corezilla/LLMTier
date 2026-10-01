"""Case ID: ST-obsstats-001

Endpoint: GET /v1/diagnostics/stats?since=...&until=...
Upstream Provider: m5air OMLX / m5mac OMLX / minimax（构造统计需一次 responses 调用）
Model: Worker（responses-capable tier；构造统计样本）
Auth: Bearer dev-admin（读写开关与读面）/ Bearer dev-data（制造统计）

TS-002 依赖：
  Endpoint: http://192.168.1.9:8181（m5air 已部署实例）
  上游: m5air OMLX 9000 / m5mac OMLX 9000 / minimax（responses 调用上游）
  模型: Worker（简洁 prompt，max_output_tokens=16）

TS-003：m5air 已部署实例自带上游，本 case 不构造新 provider endpoint。

目标：GET /v1/diagnostics/stats 返回按小时桶聚合的 StatsView：顶层恰 {windows}，
每窗口为恰好 13 键的 StatsWindow。

构造（非空断言）：先 PATCH 打开 `stats_enabled`、发起一次 `POST /v1/responses`
（入口在路由后调用 `record_latency`，落一小时桶），使 windows 非空后再断言窗口
形状与过滤语义；teardown 恢复原开关值。构造后仍为空则视为构造失败（FAIL），不再
以"空 windows 合法"放行（消除 vacuous 断言）。
"""
from __future__ import annotations

import re

import pytest

STATS_PATH = "/v1/diagnostics/stats"
DIAG_PATH = "/v1/diagnostics"
WINDOW = {"since": "2000-01-01T00:00:00Z", "until": "2100-01-01T00:00:00Z"}
STAT_HOUR_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}$")
WINDOW_KEYS = {
    "stat_hour", "deployment_id", "model", "status_breakdown",
    "error_4xx_count", "error_5xx_count", "request_count", "error_count",
    "latency_p50_ms", "latency_p95_ms", "latency_min_ms", "latency_max_ms",
    "latency_sum_ms",
}
TRACE_BODY = {
    "model": "Worker",
    "input": [{"role": "user", "content": "stats probe"}],
    "stream": True,
    "store": False,
    "max_output_tokens": 16,
}


def _restore_switches(admin_client, orig_raw: bytes) -> None:
    import json
    orig = json.loads(orig_raw)
    admin_client.patch(
        DIAG_PATH,
        json={
            "snapshots_enabled": orig.get("snapshots_enabled", False),
            "stats_enabled": orig.get("stats_enabled", False),
        },
    )


@pytest.mark.api_a
def test_obs_stats_01_windows_shape(admin_client, api_client):
    orig_raw = admin_client.get(DIAG_PATH).content
    try:
        patch = admin_client.patch(DIAG_PATH, json={"stats_enabled": True})
        assert patch.status_code == 200, f"打开 stats_enabled 失败: {patch.text}"

        with api_client.stream("POST", "/v1/responses", json=TRACE_BODY) as stream:
            for _chunk in stream.iter_bytes():
                pass

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
        assert body["windows"], (
            "构造后统计窗口仍为空——无法验证窗口级契约（构造前提未满足）"
        )

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

        # 过滤交叉核对：用本 case 实际产生的某个 deployment_id 过滤，证明过滤生效。
        observed = next(
            (w["deployment_id"] for w in body["windows"] if w["deployment_id"]), None
        )
        assert observed is not None, (
            f"构造窗口缺 deployment_id，无法做过滤核对: {body['windows']!r}"
        )
        filtered = admin_client.get(
            STATS_PATH, params={**WINDOW, "deployment_id": observed}
        )
        assert filtered.status_code == 200, (
            f"过滤请求期望 200，实际 {filtered.status_code}: {filtered.text}"
        )
        filtered_windows = filtered.json()["windows"]
        assert filtered_windows, f"按 {observed} 过滤后为空（过滤未生效）"
        for window in filtered_windows:
            assert window["deployment_id"] == observed, (
                f"过滤窗口 deployment_id 不符: {window['deployment_id']!r}"
            )
    finally:
        _restore_switches(admin_client, orig_raw)
