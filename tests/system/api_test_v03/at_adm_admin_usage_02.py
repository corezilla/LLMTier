"""Case ID: ADM-ADMIN-USAGE-02

Endpoint: GET /tier/admin/v1/usage?limit=1
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 200
- body.data.length ≤ 1
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_adm_admin_usage_02_pagination(admin_client):
    resp = admin_client.get(
        "/tier/admin/v1/usage",
        params={
            "from": "2026-09-20T00:00:00Z",
            "to": "2026-09-22T00:00:00Z",
            "limit": 1,
        },
    )
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert len(body.get("data", [])) <= 1, f"data.length > 1 但 limit=1: {body}"
