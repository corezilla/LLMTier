"""Case ID: AUTH-03

Endpoint: GET /v1/providers
Upstream Provider: 无
Model: 无
Auth: Bearer dev-data (data token, 不应授权 admin)

断言：
- HTTP 403
- error.code == "permission_denied"

注：admin 端点要求 admin token；dev-data 是 data token，权限不匹配。
"""
from __future__ import annotations

import httpx
import pytest


@pytest.mark.api_a
def test_auth_03_admin_endpoint_with_data_token():
    with httpx.Client(base_url="http://192.168.1.9:8181", timeout=10.0) as client:
        resp = client.get(
            "/v1/providers",
            headers={"Authorization": "Bearer dev-data"},
        )
    assert resp.status_code == 403, f"返回 {resp.status_code}（期望 403）: {resp.text}"
    body = resp.json()
    err = body.get("error") or {}
    assert err.get("code") == "permission_denied", f"error.code != 'permission_denied': {err}"
