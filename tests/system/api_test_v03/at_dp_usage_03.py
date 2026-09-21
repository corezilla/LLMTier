"""Case ID: DP-USAGE-03

Endpoint: GET /tier/v1/usage?limit=1
Upstream Provider: 无
Model: 无
Auth: Bearer dev-data

断言：
- HTTP 200
- body.data.length ≤ 1
- body.has_more 是 bool
- body.next_cursor 与 has_more 同步：has_more=true 时非空字符串
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_dp_usage_03_pagination(api_client):
    resp = api_client.get(
        "/tier/v1/usage",
        params={
            "from": "2026-09-20T00:00:00Z",
            "to": "2026-09-22T00:00:00Z",
            "limit": 1,
        },
    )
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert len(body.get("data", [])) <= 1, f"data.length > 1 但 limit=1: {body}"
    has_more = body.get("has_more")
    assert isinstance(has_more, bool), f"has_more 非 bool: {has_more!r}"
    next_cursor = body.get("next_cursor")
    if has_more is True:
        assert next_cursor, f"has_more=true 但 next_cursor 为空: {body}"
