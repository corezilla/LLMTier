"""Case ID: ADM-PROV-05

Endpoint: PATCH /tier/admin/v1/providers/{id}
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

依赖：先创建一个 provider（由 ADM-PROV-02 创建，或本 case 自创）

断言：
- HTTP 200
- body 含更新后的 provider
- ETag response header 存在且值比请求前新
- 字段 name / enabled 确实被更新
"""
from __future__ import annotations

import uuid

import pytest


@pytest.mark.api_b
def test_adm_prov_05_update_provider(admin_client_b):
    create_resp = admin_client_b.post("/tier/admin/v1/providers", json={
        "name": f"Provider To Update {uuid.uuid4().hex[:8]}",
        "kind": "cloud",
        "endpoint": "http://example.com/v1",
        "secret_ref": None,
        "enabled": True,
    })
    assert create_resp.status_code == 201
    provider = create_resp.json()
    rid = provider["id"]
    original_version = provider["version"]
    original_etag = create_resp.headers["ETag"]

    patch_resp = admin_client_b.patch(
        f"/tier/admin/v1/providers/{rid}",
        json={"name": "Provider Updated Name", "enabled": False},
        headers={"If-Match": original_etag},
    )
    assert patch_resp.status_code == 200, f"期望 200，实际 {patch_resp.status_code}: {patch_resp.text}"
    updated = patch_resp.json()
    assert updated["name"] == "Provider Updated Name"
    assert updated["enabled"] is False
    assert updated["version"] > original_version
    assert "ETag" in patch_resp.headers
