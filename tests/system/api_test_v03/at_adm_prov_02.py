"""Case ID: ADM-PROV-02

Endpoint: POST /tier/admin/v1/providers
Upstream Provider: 无（测试 CRUD 路由，不测 upstream）
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 201
- body 含 provider 对象（id, name, kind, endpoint, enabled, version）
- ETag response header 存在
- 可通过 GET /tier/admin/v1/providers/{id} 读取
"""
from __future__ import annotations

import uuid

import pytest


@pytest.mark.api_b
def test_adm_prov_02_create_provider(admin_client_b):
    body = {
        "name": f"Test Provider {uuid.uuid4().hex[:8]}",
        "kind": "local",
        "endpoint": "http://localhost:9999/v1",
        "secret_ref": None,
        "enabled": True,
    }
    resp = admin_client_b.post("/tier/admin/v1/providers", json=body)
    assert resp.status_code == 201, f"期望 201，实际 {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["name"] == body["name"]
    assert data["kind"] == body["kind"]
    assert data["endpoint"] == body["endpoint"]
    assert data["enabled"] == body["enabled"]
    assert "id" in data
    assert "version" in data
    assert "ETag" in resp.headers

    etag = resp.headers["ETag"]
    rid = data["id"]

    get_resp = admin_client_b.get(f"/tier/admin/v1/providers/{rid}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == body["name"]
    assert get_resp.headers.get("ETag") == etag
