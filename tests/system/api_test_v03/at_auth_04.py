"""Case ID: AUTH-04

Endpoint: GET /v1/providers
Upstream Provider: 无
Model: 无
Auth: 无（LAN trust）

断言：
- HTTP 200
- body 含 data[]
- 原因：客户端在 192.168.x LAN，LLMTIER_TRUSTED_LAN_MODE 默认开启
"""
from __future__ import annotations

import httpx
import pytest


@pytest.mark.api_a
def test_auth_04_admin_endpoint_no_token_lan_trust():
    with httpx.Client(base_url="http://192.168.1.9:8181", timeout=10.0) as client:
        resp = client.get("/v1/providers")
    assert resp.status_code == 200, f"返回 {resp.status_code}（期望 200，LAN trust）: {resp.text}"
    body = resp.json()
    assert "data" in body
