"""Case ID: AUTH-02

Endpoint: GET /v1/models
Upstream Provider: 无
Model: 无
Auth: Bearer bogus-token-xxx

断言：
- HTTP 403
- error.code == "permission_denied"

注：auth.py:56-57，Bearer token 不匹配时返回 403 permission_denied
（不是 401 authentication_required——后者是缺 Bearer 前缀时）。
"""
from __future__ import annotations

import httpx
import pytest


@pytest.mark.api_a
def test_auth_02_data_endpoint_wrong_token():
    with httpx.Client(base_url="http://192.168.1.9:8181", timeout=10.0) as client:
        resp = client.get("/v1/models", headers={"Authorization": "Bearer bogus-token-xxx"})
    assert resp.status_code == 403, f"返回 {resp.status_code}（期望 403）: {resp.text}"
    body = resp.json()
    err = body.get("error") or {}
    assert err.get("code") == "permission_denied", f"error.code != 'permission_denied': {err}"
