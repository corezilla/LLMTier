"""Case ID: ADM-PROV-07

Endpoint: PATCH /v1/providers/{id}
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- PATCH 带过期（错误）的 If-Match ETag
- HTTP 412
- error.code == "version_conflict"
- body.extra.current_version 字段存在
"""
from __future__ import annotations

import uuid

import pytest


@pytest.mark.api_b
def test_adm_prov_07_patch_wrong_etag(admin_client_b):
    create_resp = admin_client_b.post("/v1/providers", json={
        "name": f"Provider For ETag Test {uuid.uuid4().hex[:8]}",
        "kind": "local",
        "endpoint": "http://localhost:7777/v1",
        "secret_ref": None,
        "enabled": True,
    })
    assert create_resp.status_code == 201
    rid = create_resp.json()["id"]

    bad_etag = '"' + rid + '.v99"'
    patch_resp = admin_client_b.patch(
        f"/v1/providers/{rid}",
        json={"name": "Stale Update"},
        headers={"If-Match": bad_etag},
    )
    assert patch_resp.status_code == 412, f"期望 412，实际 {patch_resp.status_code}: {patch_resp.text}"
    err = patch_resp.json().get("error") or {}
    assert err.get("code") == "version_conflict"
    assert "current_version" in err, f"期望 error.current_version，实际 error={err}"
