"""Case ID: OBS-STATS-02

Endpoint: GET /v1/diagnostics/stats
Upstream Provider: 无（仅诊断读面；不触上游）
Model: 无
Auth: Bearer dev-admin

TS-002 依赖：
  Endpoint: http://192.168.1.9:8181（m5air 已部署实例）
  上游: 无（本 case 不触上游）
  模型: 无

TS-003：不触上游，无 provider endpoint。

目标：GET /v1/diagnostics/stats 缺少必填 since/until：HTTP 400 invalid_request，
且不落到空窗口的 200。空串 since= 因 parse_qs 默认 keep_blank_values=False 被丢弃，
等价于缺参 → 同样 400。
"""
from __future__ import annotations

import pytest

STATS_PATH = "/v1/diagnostics/stats"
MISSING_PARAM_CASES = [
    {},
    {"since": "2000-01-01T00:00:00Z"},
    {"until": "2100-01-01T00:00:00Z"},
    {"since": ""},
    {"until": ""},
]


@pytest.mark.api_a
def test_obs_stats_02_missing_window_400(admin_client):
    for params in MISSING_PARAM_CASES:
        resp = admin_client.get(STATS_PATH, params=params)
        assert resp.status_code == 400, (
            f"params={params} 期望 400，实际 {resp.status_code}: {resp.text}"
        )
        err = resp.json()["error"]
        assert set(err.keys()) == {"message", "type", "code", "param", "retryable"}, (
            f"错误信封键集不符: {sorted(err.keys())}"
        )
        assert err["code"] == "invalid_request", f"params={params} code 不符: {err}"
        assert err["type"] == "request_error", f"params={params} type 不符: {err}"
        assert err["retryable"] is False, f"params={params} retryable 应为 False: {err}"

    control = admin_client.get(
        STATS_PATH,
        params={"since": "2000-01-01T00:00:00Z", "until": "2100-01-01T00:00:00Z"},
    )
    assert control.status_code == 200, (
        f"对照期望 200，实际 {control.status_code}: {control.text}"
    )
    assert set(control.json().keys()) == {"windows"}, (
        f"对照顶层键集应恰为 {{windows}}: {sorted(control.json().keys())}"
    )
