"""Case ID: ADM-STATS-03

Endpoint: GET /v1/stats (缺 from/to)
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 400
- error.code == "invalid_request"
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_adm_stats_03_missing_time_range(admin_client):
    resp = admin_client.get("/v1/stats")
    assert resp.status_code == 400, f"返回 {resp.status_code}（期望 400）: {resp.text}"
    body = resp.json()
    err = body.get("error") or {}
    assert err.get("code") == "invalid_request", f"error.code != 'invalid_request': {err}"
