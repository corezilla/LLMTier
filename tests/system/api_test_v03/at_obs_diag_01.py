"""Case ID: ST-OBSDIAG-001

Endpoint: GET /v1/diagnostics
Upstream Provider: 无（仅诊断读面；不触上游）
Model: 无
Auth: Bearer dev-admin

TS-002 依赖：
  Endpoint: http://192.168.1.9:8181（m5air 已部署实例）
  上游: 无（本 case 不触上游）
  模型: 无

TS-003：不触上游，无 provider endpoint。

目标：GET /v1/diagnostics 读取全局诊断开关：HTTP 200 + 精确 SwitchState
（键集恰 {snapshots_enabled, stats_enabled}，两值均为 JSON 布尔），纯读无副作用。
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_obs_diag_01_switches_shape(admin_client):
    resp = admin_client.get("/v1/diagnostics")
    assert resp.status_code == 200, (
        f"期望 200，实际 {resp.status_code}: {resp.text}"
    )
    assert "application/json" in resp.headers.get("content-type", ""), (
        f"Content-Type 非 JSON: {resp.headers.get('content-type')}"
    )
    body = resp.json()
    assert set(body.keys()) == {"snapshots_enabled", "stats_enabled"}, (
        f"SwitchState 键集应恰为 {{snapshots_enabled, stats_enabled}}: {sorted(body.keys())}"
    )
    assert type(body["snapshots_enabled"]) is bool, (
        f"snapshots_enabled 应为 JSON 布尔: {body['snapshots_enabled']!r}"
    )
    assert type(body["stats_enabled"]) is bool, (
        f"stats_enabled 应为 JSON 布尔: {body['stats_enabled']!r}"
    )
