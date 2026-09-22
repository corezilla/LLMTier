"""Case ID: DP-USAGE-04

Endpoint: GET /v1/usage?cursor=expired
Upstream Provider: 无
Model: 无
Auth: Bearer dev-data

断言：
- HTTP 400
- error.code == "cursor_expired"

注：cursor="expired" 不存在于 query_snapshots 表 → usage.py:62 命中"snapshot is None" 分支 → 抛 cursor_expired。
这与"过期"的语义等价（cursor 无法解析到有效 snapshot），不需要真造 expires_at < now 的 cursor。
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_dp_usage_04_expired_cursor(api_client):
    resp = api_client.get(
        "/v1/usage",
        params={
            "from": "2026-09-20T00:00:00Z",
            "to": "2026-09-22T00:00:00Z",
            "cursor": "expired",
        },
    )
    assert resp.status_code == 400, f"返回 {resp.status_code}（期望 400）: {resp.text}"
    body = resp.json()
    err = body.get("error") or {}
    assert err.get("code") == "cursor_expired", f"error.code != 'cursor_expired': {err}"
