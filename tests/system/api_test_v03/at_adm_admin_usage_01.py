"""Case ID: ADM-ADMIN-USAGE-01

Endpoint: GET /v1/usage?from=...&to=...
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 200
- body 含 data / next_cursor / has_more / snapshot_id / snapshot_at
"""
from __future__ import annotations

import pytest

from tests.system.api_test_v03.constants import recent_window


@pytest.mark.api_a
def test_adm_admin_usage_01(admin_client):
    since, until = recent_window()
    resp = admin_client.get(
        "/v1/usage",
        params={"from": since, "to": until},
    )
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    for field in ("data", "next_cursor", "has_more", "snapshot_id", "snapshot_at"):
        assert field in body, f"缺 {field}: {body}"
