"""Case ID: DP-USAGE-01

Endpoint: GET /tier/v1/usage
Upstream Provider: 无
Model: 无
Auth: Bearer dev-data

断言：
- HTTP 200
- body.data 是数组（可能空或非空——m5air 有历史 usage）
- body.next_cursor 与 has_more 同步：has_more=false 时 next_cursor=null
- body 含 snapshot_id、snapshot_at
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_dp_usage_01_queryable(api_client):
    resp = api_client.get(
        "/tier/v1/usage",
        params={"from": "2026-09-20T00:00:00Z", "to": "2026-09-22T00:00:00Z"},
    )
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert isinstance(body.get("data"), list), "data 非数组"
    has_more = body.get("has_more")
    next_cursor = body.get("next_cursor")
    if has_more is False:
        assert next_cursor is None, f"has_more=false 但 next_cursor={next_cursor!r}"
    assert "snapshot_id" in body, f"缺 snapshot_id: {body}"
    assert "snapshot_at" in body, f"缺 snapshot_at: {body}"
