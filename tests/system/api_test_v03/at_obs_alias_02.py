"""Case ID: ST-OBSALIAS-002

Endpoint: GET /tier/admin/v1/diagnostics/snapshots ≡ /v1/diagnostics/snapshots
Upstream Provider: 无（诊断读面；不触上游）
Model: 无
Auth: Bearer dev-admin

TS-002 依赖：
  Endpoint: http://192.168.1.9:8181（m5air 已部署实例）
  上游: 无（本 case 不触上游）
  模型: 无

TS-003：不触上游，无 provider endpoint。

目标：快照查询别名与扁平路径由同一 handler 服务：status 与响应体逐字节等价。
"""
from __future__ import annotations

import pytest

FLAT = "/v1/diagnostics/snapshots"
ALIAS = "/tier/admin/v1/diagnostics/snapshots"
PARAMS = {"limit": 50}


@pytest.mark.api_a
def test_obs_alias_02_snapshots_equivalence(admin_client):
    flat = admin_client.get(FLAT, params=PARAMS)
    alias = admin_client.get(ALIAS, params=PARAMS)
    assert flat.status_code == 200, f"扁平路径期望 200，实际 {flat.status_code}: {flat.text}"
    assert alias.status_code == 200, f"别名路径期望 200，实际 {alias.status_code}: {alias.text}"
    assert flat.content == alias.content, (
        f"body 非逐字节等价: {flat.json()} != {alias.json()}"
    )
    assert set(flat.json().keys()) == {"items", "next_cursor", "has_more"}, (
        f"非合法 SnapshotPage: {sorted(flat.json().keys())}"
    )
