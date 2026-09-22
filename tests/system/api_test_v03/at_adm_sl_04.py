"""Case ID: ADM-SL-04

Endpoint: PATCH /v1/service-levels/{id}
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

前置条件：FIXED_TIER "Junior" 已存在（baseline 预创建）

断言：
- PATCH 带正确 If-Match，body 含 {"enabled": false}
- HTTP 200
- body.enabled == false
- ETag 值比请求前新
"""
from __future__ import annotations

import pytest


@pytest.mark.api_b
def test_adm_sl_04_update_service_level(admin_client_b):
    get_resp = admin_client_b.get("/v1/service-levels/Junior")
    assert get_resp.status_code == 200
    tier = get_resp.json()
    original_etag = get_resp.headers.get("ETag")
    assert tier["enabled"] is True, "期望 baseline Junior 为 enabled=True"

    patch_resp = admin_client_b.patch(
        "/v1/service-levels/Junior",
        json={"enabled": False},
        headers={"If-Match": original_etag},
    )
    assert patch_resp.status_code == 200, f"期望 200，实际 {patch_resp.status_code}: {patch_resp.text}"
    updated = patch_resp.json()
    assert updated["enabled"] is False
    assert updated["version"] > tier["version"]
    assert "ETag" in patch_resp.headers
