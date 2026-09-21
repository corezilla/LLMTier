"""Case ID: ADM-SL-02b

Endpoint: POST /tier/admin/v1/service-levels
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

前置条件：FIXED_TIER "Senior" 已存在（baseline 预创建）

断言：
- POST body.id == "Senior"（已存在）
- HTTP 409
- error.code == "resource_conflict"
"""
from __future__ import annotations

import pytest


@pytest.mark.api_b
def test_adm_sl_02b_create_duplicate_fixed_tier(admin_client_b):
    resp = admin_client_b.post("/tier/admin/v1/service-levels", json={
        "id": "Senior",
        "deployment_ids": ["depl_b"],
        "enabled": True,
    })
    assert resp.status_code == 409, f"期望 409，实际 {resp.status_code}: {resp.text}"
    err = resp.json().get("error") or {}
    assert err.get("code") == "resource_conflict"
