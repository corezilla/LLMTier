"""Case ID: ADM-SL-06

Endpoint: PATCH /tier/admin/v1/service-levels/{id}
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

目标：验证 capability_conflict → 409。

触发方式：PATCH 现有 fixed tier（Senior），改其 deployment_ids 为两个 context_window 不同的 deployment。

原理：registry.py:265-273 `_capability_intersection` 对 non-boolean 值执行 `all(v == values[0])`。
context_window 不一致（如 4096 vs 8192）时该 key 被丢弃，
导致 `set(capabilities) != CAPABILITY_KEYS` → registry.py:282 → 409。

断言：
- HTTP 409
- error.code == "capability_conflict"
"""
from __future__ import annotations

import pytest


@pytest.mark.api_b
def test_adm_sl_06_capability_conflict(admin_client_b):
    get_resp = admin_client_b.get("/tier/admin/v1/service-levels/Senior")
    assert get_resp.status_code == 200
    etag = get_resp.headers.get("ETag")

    new_depl = admin_client_b.post("/tier/admin/v1/deployments", json={
        "name": "Deployment Different Context",
        "provider_id": "prov_b",
        "backend_model": "model-diff-context",
        "capabilities": {
            "responses": True,
            "embeddings": False,
            "tools": True,
            "structured_outputs": False,
            "input_modalities": ["text"],
            "output_modalities": ["text"],
            "context_window": 8192,
            "max_output_tokens": 2048,
            "embedding_space_id": None,
            "embedding_dimensions": None,
            "embedding_max_batch_inputs": None,
            "embedding_max_input_tokens": None,
        },
        "enabled": True,
    })
    assert new_depl.status_code == 201
    new_depl_id = new_depl.json()["id"]

    patch_resp = admin_client_b.patch(
        "/tier/admin/v1/service-levels/Senior",
        json={"deployment_ids": ["depl_b", new_depl_id]},
        headers={"If-Match": etag},
    )
    assert patch_resp.status_code == 409, f"期望 409，实际 {patch_resp.status_code}: {patch_resp.text}"
    err = patch_resp.json().get("error") or {}
    assert err.get("code") == "capability_conflict"
