"""Case ID: ADM-PROV-09

Endpoint: DELETE /v1/providers/{id}
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- DELETE 不带 If-Match header
- HTTP 412
- error.code == "version_conflict"
- body.extra.current_version 存在
"""
from __future__ import annotations

import uuid

import pytest


@pytest.mark.api_b
def test_adm_prov_09_delete_missing_if_match(admin_client_b):
    create_resp = admin_client_b.post("/v1/providers", json={
        "name": f"Provider To Delete Without Etag {uuid.uuid4().hex[:8]}",
        "kind": "local",
        "endpoint": "http://localhost:5555/v1",
        "secret_ref": None,
        "enabled": True,
    })
    assert create_resp.status_code == 201
    rid = create_resp.json()["id"]

    del_resp = admin_client_b.delete(f"/v1/providers/{rid}")
    assert del_resp.status_code == 412, f"期望 412，实际 {del_resp.status_code}: {del_resp.text}"
    err = del_resp.json().get("error") or {}
    assert err.get("code") == "version_conflict"
    assert "current_version" in err, f"期望 error.current_version，实际 error={err}"
