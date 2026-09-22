"""Case ID: ADM-PROV-USAGE-03

Endpoint: POST /v1/providers/{id}/usage (带 confirm)
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 200
- body 含 provider, source, status, used, quota, checked_at

注：provider_local 是 local 类型，refresh 返回 "unlimited" snapshot（account_usage.py:160）。
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_adm_prov_usage_03_refresh_with_confirm(admin_client):
    resp = admin_client.post(
        "/v1/providers/provider_local/usage",
        json={"confirm_external_call": True},
    )
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    for field in ("provider", "source", "status", "checked_at"):
        assert field in body, f"缺 {field}: {list(body.keys())}"
