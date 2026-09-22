"""Case ID: ADM-PROV-04

Endpoint: GET /v1/providers/{id} (不存在)
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 404
- error.code == "not_found"
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_adm_prov_04_get_nonexistent(admin_client):
    resp = admin_client.get("/v1/providers/provider_does_not_exist_xyz")
    assert resp.status_code == 404, f"返回 {resp.status_code}（期望 404）: {resp.text}"
    body = resp.json()
    err = body.get("error") or {}
    assert err.get("code") == "not_found", f"error.code != 'not_found': {err}"
