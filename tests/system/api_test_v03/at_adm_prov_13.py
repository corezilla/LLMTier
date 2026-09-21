"""Case ID: ADM-PROV-13

Endpoint: PATCH /tier/admin/v1/providers/{id}
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

目标：验证 usage 子对象更新（max_concurrent_requests）。

断言：
- HTTP 200
- 更新后 GET 能读到新值
"""
from __future__ import annotations

import pytest


@pytest.mark.api_b
def test_adm_prov_13_usage_subobject_update(admin_client_b):
    patch_resp = admin_client_b.patch(
        "/tier/admin/v1/providers/prov_b",
        json={"usage": {"max_concurrent_requests": 5}},
        headers={"If-Match": '"prov_b.v1"'},
    )
    assert patch_resp.status_code == 200, f"期望 200，实际 {patch_resp.status_code}: {patch_resp.text}"

    get_resp = admin_client_b.get("/tier/admin/v1/providers/prov_b")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data.get("usage", {}).get("max_concurrent_requests") == 5
