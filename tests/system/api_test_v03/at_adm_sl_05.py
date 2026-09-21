"""Case ID: ADM-SL-05

Endpoint: DELETE /tier/admin/v1/service-levels/{id}
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- DELETE 任意 FIXED_TIER（如 "Engineer"）
- HTTP 409
- error.code == "fixed_service_level"
- error.message 包含 "cannot be deleted"
"""
from __future__ import annotations

import pytest


@pytest.mark.api_b
def test_adm_sl_05_delete_fixed_tier(admin_client_b):
    get_resp = admin_client_b.get("/tier/admin/v1/service-levels/Engineer")
    assert get_resp.status_code == 200
    etag = get_resp.headers.get("ETag")

    del_resp = admin_client_b.delete(
        "/tier/admin/v1/service-levels/Engineer",
        headers={"If-Match": etag},
    )
    assert del_resp.status_code == 409, f"期望 409，实际 {del_resp.status_code}: {del_resp.text}"
    err = del_resp.json().get("error") or {}
    assert err.get("code") == "fixed_service_level"
    assert "cannot be deleted" in err.get("message", "")
