"""Case ID: ADM-PROV-06

Endpoint: PATCH /tier/admin/v1/providers/{id}
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

前置条件：已有 provider（来自测试内创建）

断言：
- PATCH 不带 If-Match header
- HTTP 412
- error.code == "version_conflict"
- body.extra.current_version 字段存在
"""
from __future__ import annotations

import uuid

import pytest


@pytest.mark.api_b
def test_adm_prov_06_patch_missing_if_match(admin_client_b):
    create_resp = admin_client_b.post("/tier/admin/v1/providers", json={
        "name": f"Provider For Patch Test {uuid.uuid4().hex[:8]}",
        "kind": "local",
        "endpoint": "http://localhost:8888/v1",
        "secret_ref": None,
        "enabled": True,
    })
    assert create_resp.status_code == 201
    rid = create_resp.json()["id"]

    patch_resp = admin_client_b.patch(
        f"/tier/admin/v1/providers/{rid}",
        json={"name": "Should Not Be Applied"},
    )
    assert patch_resp.status_code == 412, f"期望 412，实际 {patch_resp.status_code}: {patch_resp.text}"
    err = patch_resp.json().get("error") or {}
    assert err.get("code") == "version_conflict"
    assert "current_version" in err, f"期望 error.current_version，实际 error={err}"
