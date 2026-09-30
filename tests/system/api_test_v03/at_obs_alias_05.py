"""Case ID: OBS-ALIAS-05

Endpoint: GET /tier/admin/v1/diagnostics/stats ≡ /v1/diagnostics/stats
Upstream Provider: 无（诊断读面；不触上游）
Model: 无
Auth: Bearer dev-admin

TS-002 依赖：
  Endpoint: http://192.168.1.9:8181（m5air 已部署实例）
  上游: 无（本 case 不触上游）
  模型: 无

TS-003：不触上游，无 provider endpoint。

目标：诊断统计别名与扁平路径由同一 handler 服务：status 与响应体逐字节等价
（含缺参 400 信封）。
"""
from __future__ import annotations

import pytest

FLAT = "/v1/diagnostics/stats"
ALIAS = "/tier/admin/v1/diagnostics/stats"
WINDOW = {"since": "2000-01-01T00:00:00Z", "until": "2100-01-01T00:00:00Z"}


@pytest.mark.api_a
def test_obs_alias_05_stats_equivalence(admin_client):
    flat = admin_client.get(FLAT, params=WINDOW)
    alias = admin_client.get(ALIAS, params=WINDOW)
    assert flat.status_code == 200, f"扁平正向期望 200，实际 {flat.status_code}: {flat.text}"
    assert alias.status_code == 200, f"别名正向期望 200，实际 {alias.status_code}: {alias.text}"
    assert flat.content == alias.content, (
        f"正向 body 非逐字节等价: {flat.json()} != {alias.json()}"
    )
    assert set(flat.json().keys()) == {"windows"}, f"非合法 StatsView: {flat.json()}"

    flat_400 = admin_client.get(FLAT)
    alias_400 = admin_client.get(ALIAS)
    assert flat_400.status_code == 400, f"缺参扁平期望 400，实际 {flat_400.status_code}"
    assert alias_400.status_code == 400, f"缺参别名期望 400，实际 {alias_400.status_code}"
    assert flat_400.content == alias_400.content, (
        f"400 信封非逐字节等价: {flat_400.json()} != {alias_400.json()}"
    )
    assert flat_400.json()["error"]["code"] == "invalid_request", (
        f"code 不符: {flat_400.json()}"
    )
