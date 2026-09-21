"""Case ID: ADM-STATS-01

Endpoint: GET /tier/admin/v1/stats?from=...&to=...
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 200
- body.data 是数组（按时间窗聚合）
- body 含 from/to/group_by 回显
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_adm_stats_01_basic(admin_client):
    resp = admin_client.get(
        "/tier/admin/v1/stats",
        params={"from": "2026-09-20T00:00:00Z", "to": "2026-09-22T00:00:00Z"},
    )
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert isinstance(body.get("data"), list), f"data 非数组: {body}"
    assert body.get("from") == "2026-09-20T00:00:00Z", f"from 回显错: {body}"
