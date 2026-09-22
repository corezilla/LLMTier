"""Case ID: ADM-PROV-10

Endpoint: DELETE /v1/providers/{id}
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

前置条件：provider 有 active deployment（prov_b → depl_b，来自 _BASELINE_SETTINGS）

断言：
- DELETE 带正确 If-Match
- HTTP 409
- error.code == "resource_in_use"
- error.message 包含 "referenced by"
"""
from __future__ import annotations

import pytest


@pytest.mark.api_b
def test_adm_prov_10_delete_provider_with_active_deployment(admin_client_b):
    r = admin_client_b.delete(
        "/v1/providers/prov_b",
        headers={"If-Match": '"prov_b.v1"'},
    )
    assert r.status_code == 409, f"期望 409，实际 {r.status_code}: {r.text}"
    err = r.json().get("error") or {}
    assert err.get("code") == "resource_in_use"
    assert "referenced" in err.get("message", "").lower()
