"""Case ID: ADM-ADMIN-USAGE-01

Endpoint: GET /tier/admin/v1/usage?from=...&to=...
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 200
- body 含 data / next_cursor / has_more / snapshot_id / snapshot_at
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_adm_admin_usage_01(admin_client):
    resp = admin_client.get(
        "/tier/admin/v1/usage",
        params={"from": "2026-09-20T00:00:00Z", "to": "2026-09-22T00:00:00Z"},
    )
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    for field in ("data", "next_cursor", "has_more", "snapshot_id", "snapshot_at"):
        assert field in body, f"缺 {field}: {body}"
