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


@pytest.mark.api_a
def test_adm_stats_02_group_by_tier(admin_client):
    resp = admin_client.get(
        "/v1/stats",
        params={
            "from": "2026-09-20T00:00:00Z",
            "to": "2026-09-22T00:00:00Z",
            "group_by": "tier",
        },
    )
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body.get("group_by") == "tier", f"group_by != 'tier': {body}"
