"""Case ID: OBS-ALIAS-04

Endpoint: GET/PATCH /tier/admin/v1/deployments/{id}/diagnostics ≡ /v1/deployments/{id}/diagnostics
Upstream Provider: prov_b（LAN IP fake provider，TS-003）
Model: depl_b（backend_model=test-model）
Auth: Bearer dev-admin

TS-002 依赖：
  Endpoint: 专用临时 LLMTier 实例（llmtier_b，独立临时 SQLite/端口）
  上游: prov_b 指向 LAN IP 上的 fake provider（TS-003）
  模型: depl_b / test-model

TS-003：本 case 不触发推理，无 provider endpoint 请求。

目标：注入配置别名与扁平路径由同一 handler 服务：GET body 逐字节等价；PATCH 因
updated_at 为服务端时间戳，等价判定为除 updated_at 外逐字段相等。teardown 清空。
"""
from __future__ import annotations

import pytest

FLAT = "/v1/deployments/depl_b/diagnostics"
ALIAS = "/tier/admin/v1/deployments/depl_b/diagnostics"
BODY = {"items": [{"type": "delay", "config": {"delay_ms": 1000}, "enabled": True}]}


def _sorted_key(items):
    return sorted(
        {k: v for k, v in item.items() if k != "updated_at"}.items()
        for item in items
    )


@pytest.mark.api_b
def test_obs_alias_04_deployments_injections_equivalence(llmtier_b):
    client = llmtier_b.admin_client()
    try:
        patch_flat = client.patch(FLAT, json=BODY)
        assert patch_flat.status_code == 200, f"扁平 PATCH 期望 200: {patch_flat.text}"

        get_flat = client.get(FLAT)
        get_alias = client.get(ALIAS)
        assert get_flat.status_code == get_alias.status_code == 200, (
            f"GET status 不等价: flat={get_flat.status_code} alias={get_alias.status_code}"
        )
        assert get_flat.content == get_alias.content, (
            f"GET body 非逐字节等价: {get_flat.json()} != {get_alias.json()}"
        )

        patch_alias = client.patch(ALIAS, json=BODY)
        assert patch_alias.status_code == patch_flat.status_code == 200, (
            f"PATCH status 不等价: flat={patch_flat.status_code} alias={patch_alias.status_code}"
        )
        assert len(patch_flat.json()) == len(patch_alias.json()), (
            f"PATCH 数组长度不等: {len(patch_flat.json())} != {len(patch_alias.json())}"
        )
        assert _sorted_key(patch_flat.json()) == _sorted_key(patch_alias.json()), (
            f"PATCH 除 updated_at 外字段不等: {patch_flat.json()} != {patch_alias.json()}"
        )
    finally:
        cleared = client.patch(FLAT, json={"items": []})
        final_flat = client.get(FLAT)
        final_alias = client.get(ALIAS)
        client.close()
    assert cleared.status_code == 200 and cleared.json() == [], f"teardown 清空失败: {cleared.text}"
    assert final_flat.content == final_alias.content == b'[]', (
        f"teardown 后两路径应均为 [] 且等价: {final_flat.json()} != {final_alias.json()}"
    )
