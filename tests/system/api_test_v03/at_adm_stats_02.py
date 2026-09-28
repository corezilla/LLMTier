"""Case ID: ADM-STATS-02

Endpoint: GET /v1/stats?from=...&to=...&group_by=tier
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 200
- body.group_by == "tier"
"""
from __future__ import annotations

import pytest

from tests.system.api_test_v03.constants import recent_window


@pytest.mark.api_a
def test_adm_stats_02_group_by_tier(admin_client):
    since, until = recent_window()
    resp = admin_client.get(
        "/v1/stats",
        params={
            "from": since,
            "to": until,
            "group_by": "tier",
        },
    )
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body.get("group_by") == "tier", f"group_by != 'tier': {body}"
