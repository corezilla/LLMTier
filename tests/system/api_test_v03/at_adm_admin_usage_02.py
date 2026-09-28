"""Case ID: ADM-ADMIN-USAGE-02

Endpoint: GET /v1/usage?limit=1
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 200
- body.data.length ≤ 1
"""
from __future__ import annotations

import pytest

from tests.system.api_test_v03.constants import recent_window


@pytest.mark.api_a
def test_adm_admin_usage_02_pagination(admin_client):
    since, until = recent_window()
    resp = admin_client.get(
        "/v1/usage",
        params={
            "from": since,
            "to": until,
            "limit": 1,
        },
    )
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert len(body.get("data", [])) <= 1, f"data.length > 1 但 limit=1: {body}"
