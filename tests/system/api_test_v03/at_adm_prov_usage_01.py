"""Case ID: ADM-PROV-USAGE-01

Endpoint: GET /tier/admin/v1/providers/{id}/usage
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 200
- body 含 provider, source, status, checked_at 等字段
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_adm_prov_usage_01_get_snapshot(admin_client):
    resp = admin_client.get("/tier/admin/v1/providers/provider_local/usage")
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    for field in ("provider", "source", "status", "checked_at"):
        assert field in body, f"缺 {field}: {list(body.keys())}"
