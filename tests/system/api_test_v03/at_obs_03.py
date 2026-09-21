"""Case ID: OBS-03

Endpoint: GET /readyz
Upstream Provider: 无（无 deployments）
Model: 无
Auth: 无（公共端点）

前置条件：临时实例使用 _EMPTY_SETTINGS（无 providers，无 deployments）

断言：
- HTTP 200 或 503（两者皆可，只要 body 结构正确）
- body.models[].id 属于 FIXED_TIERS
- body.models[].availability == "unavailable"（因为无任何 deployment）
- body.status == "not_ready"
"""
from __future__ import annotations

import pytest


@pytest.mark.api_b
def test_obs_03_no_deployments_readyz(admin_client_b_empty):
    resp = admin_client_b_empty.get("/readyz")
    assert resp.status_code in (200, 503), f"期望 200/503，实际 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert "models" in body
    models = body["models"]
    assert len(models) == 7, f"期望 7 个 FIXED_TIERS，实际 {len(models)}"
    ids = {m["id"] for m in models}
    expected = {"Senior", "Junior", "Worker", "Associate", "Engineer", "Executor", "Embedding-v1"}
    assert ids == expected, f"ID 不匹配: {ids} vs {expected}"
    for m in models:
        assert m["availability"] == "unavailable", f"期望 unavailable，实际 {m['availability']}"
    assert body["status"] == "not_ready", f"期望 not_ready，实际 {body['status']}"
