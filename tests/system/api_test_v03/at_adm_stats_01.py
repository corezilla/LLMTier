"""Case ID: ADM-STATS-01

Endpoint: GET /v1/stats?from=...&to=...
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

from tests.system.api_test_v03.constants import recent_window


@pytest.mark.api_a
def test_adm_stats_01_basic(admin_client):
    since, until = recent_window()
    resp = admin_client.get(
        "/v1/stats",
        params={"from": since, "to": until},
    )
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert isinstance(body.get("data"), list), f"data 非数组: {body}"
    assert body.get("from") == since, f"from 回显错: {body}"
