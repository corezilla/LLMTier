"""Case ID: ADM-SL-04b

Endpoint: PATCH /tier/admin/v1/service-levels/{id}
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- PATCH body 含未知字段（如 {"unknown_field": "x"}）
- HTTP 400
- error.code == "invalid_request"
- error.message 含 "Unknown or empty"
"""
from __future__ import annotations

import pytest


@pytest.mark.api_b
def test_adm_sl_04b_update_with_unknown_field(admin_client_b):
    get_resp = admin_client_b.get("/tier/admin/v1/service-levels/Worker")
    assert get_resp.status_code == 200
    etag = get_resp.headers.get("ETag")

    patch_resp = admin_client_b.patch(
        "/tier/admin/v1/service-levels/Worker",
        json={"unknown_field": "value"},
        headers={"If-Match": etag},
    )
    assert patch_resp.status_code == 400, f"期望 400，实际 {patch_resp.status_code}: {patch_resp.text}"
    err = patch_resp.json().get("error") or {}
    assert err.get("code") == "invalid_request"
    assert "Unknown or empty" in err.get("message", "")
