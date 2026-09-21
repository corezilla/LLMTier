"""Case ID: ADM-SL-02

Endpoint: POST /tier/admin/v1/service-levels
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- POST body.id 不是 FIXED_TIER（如 "CustomTier"）
- HTTP 400
- error.code == "invalid_request"
- error.field == "id"
"""
from __future__ import annotations

import pytest


@pytest.mark.api_b
def test_adm_sl_02_create_non_fixed_tier(admin_client_b):
    resp = admin_client_b.post("/tier/admin/v1/service-levels", json={
        "id": "CustomTier",
        "deployment_ids": ["depl_b"],
        "enabled": True,
    })
    assert resp.status_code == 400, f"期望 400，实际 {resp.status_code}: {resp.text}"
    err = resp.json().get("error") or {}
    assert err.get("code") == "invalid_request"
    assert err.get("param") == "id"
    assert "not a fixed Tier" in err.get("message", "")
