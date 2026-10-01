"""Case ID: ST-obsalias-001

Endpoint: GET/PATCH /tier/admin/v1/diagnostics ≡ /v1/diagnostics
Upstream Provider: 无（诊断开关面；不触上游）
Model: 无
Auth: Bearer dev-admin

TS-002 依赖：
  Endpoint: http://192.168.1.9:8181（m5air 已部署实例）
  上游: 无（本 case 不触上游）
  模型: 无

TS-003：不触上游，无 provider endpoint。

目标：/tier/admin/v1/diagnostics 与 /v1/diagnostics 的 GET/PATCH 由同一 handler
服务：status 与响应体逐字节等价。PATCH 后 teardown 恢复原值。
"""
from __future__ import annotations

import pytest

FLAT = "/v1/diagnostics"
ALIAS = "/tier/admin/v1/diagnostics"


@pytest.mark.api_a
def test_obs_alias_01_diagnostics_equivalence(admin_client):
    client = admin_client
    flat_get = client.get(FLAT)
    alias_get = client.get(ALIAS)
    assert flat_get.status_code == alias_get.status_code == 200, (
        f"GET status 不等价: flat={flat_get.status_code} alias={alias_get.status_code}"
    )
    assert flat_get.content == alias_get.content, (
        f"GET body 非逐字节等价: {flat_get.json()} != {alias_get.json()}"
    )
    baseline = client.get(FLAT)
    orig = baseline.json()
    orig_raw = baseline.content

    body = {"snapshots_enabled": not orig["snapshots_enabled"], "stats_enabled": orig["stats_enabled"]}
    try:
        patch_flat = client.patch(FLAT, json=body)
        patch_alias = client.patch(ALIAS, json=body)
        assert patch_flat.status_code == patch_alias.status_code == 200, (
            f"PATCH status 不等价: flat={patch_flat.status_code} alias={patch_alias.status_code}"
        )
        assert patch_flat.content == patch_alias.content, (
            f"PATCH body 非逐字节等价: {patch_flat.json()} != {patch_alias.json()}"
        )
    finally:
        restored = client.patch(
            FLAT,
            json={"snapshots_enabled": orig["snapshots_enabled"], "stats_enabled": orig["stats_enabled"]},
        )
        final = client.get(FLAT)
    assert restored.status_code == 200, f"teardown PATCH 期望 200: {restored.text}"
    assert final.content == orig_raw, f"teardown 未恢复原值: {final.json()} != {orig}"
