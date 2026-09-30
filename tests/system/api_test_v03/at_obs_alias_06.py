"""Case ID: OBS-ALIAS-06

Endpoint: GET /tier/admin/v1/diagnostics/traces ≡ /v1/diagnostics/traces
Upstream Provider: 无（诊断读面；不触上游）
Model: 无
Auth: Bearer dev-admin

TS-002 依赖：
  Endpoint: http://192.168.1.9:8181（m5air 已部署实例）
  上游: 无（本 case 不触上游）
  模型: 无

TS-003：不触上游，无 provider endpoint。

目标：trace 列表别名与扁平路径由同一 handler 服务：status 与响应体逐字节等价
（含无效 cursor 路径的等价观察，只判两路径行为一致，不判 cursor 负向本身）。
"""
from __future__ import annotations

import pytest

FLAT = "/v1/diagnostics/traces"
ALIAS = "/tier/admin/v1/diagnostics/traces"


@pytest.mark.api_a
def test_obs_alias_06_traces_equivalence(admin_client):
    flat = admin_client.get(FLAT, params={"limit": 50})
    alias = admin_client.get(ALIAS, params={"limit": 50})
    assert flat.status_code == alias.status_code == 200, (
        f"正向 status 不等价: flat={flat.status_code} alias={alias.status_code}"
    )
    assert flat.content == alias.content, (
        f"正向 body 非逐字节等价: {flat.json()} != {alias.json()}"
    )
    assert set(flat.json().keys()) == {"items", "next_cursor", "has_more"}, (
        f"非合法 TracePage: {sorted(flat.json().keys())}"
    )

    params = {"limit": 1, "cursor": "not-a-real-cursor"}
    flat_edge = admin_client.get(FLAT, params=params)
    alias_edge = admin_client.get(ALIAS, params=params)
    assert flat_edge.status_code == alias_edge.status_code, (
        f"边界 status 不等价: flat={flat_edge.status_code} alias={alias_edge.status_code}"
    )
    assert flat_edge.content == alias_edge.content, (
        f"边界 body 非逐字节等价: {flat_edge.json()} != {alias_edge.json()}"
    )
