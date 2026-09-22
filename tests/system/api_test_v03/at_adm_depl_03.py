"""Case ID: ADM-DEPL-03

Endpoint: GET /v1/deployments/{id}
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 200
- 含 id, name, provider_id, backend_model, enabled, version
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_adm_depl_03_get_existing(admin_client):
    resp = admin_client.get("/v1/deployments/dep_local_gemma")
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    for field in ("id", "name", "provider_id", "backend_model", "enabled", "version"):
        assert field in body, f"缺字段 {field}: {body}"
    assert body["id"] == "dep_local_gemma"
