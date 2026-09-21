"""Case ID: ADM-PROV-USAGE-02

Endpoint: POST /tier/admin/v1/providers/{id}/usage (body 不是 {confirm_external_call})
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 400
- error.code == "invalid_request"

注：app.py:136 先于 account_usage.py:151 检查 body 集合 == {confirm_external_call}。
空 body {} → set != → 抛 invalid_request 而非 confirmation_required。
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_adm_prov_usage_02_invalid_body(admin_client):
    resp = admin_client.post(
        "/tier/admin/v1/providers/provider_local/usage", json={},
    )
    assert resp.status_code == 400, f"返回 {resp.status_code}（期望 400）: {resp.text}"
    body = resp.json()
    err = body.get("error") or {}
    assert err.get("code") == "invalid_request", f"error.code != 'invalid_request': {err}"
