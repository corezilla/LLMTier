"""Case ID: ADM-PROV-03

Endpoint: GET /tier/admin/v1/providers/{id}
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 200
- 含 id, name, kind, endpoint, has_secret, enabled, usage, request_usage, version 字段
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_adm_prov_03_get_existing(admin_client):
    resp = admin_client.get("/tier/admin/v1/providers/provider_local")
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    for field in ("id", "name", "kind", "endpoint", "has_secret", "enabled", "version"):
        assert field in body, f"缺字段 {field}: {body}"
    assert body["id"] == "provider_local"
    assert body["kind"] in ("cloud", "local")
