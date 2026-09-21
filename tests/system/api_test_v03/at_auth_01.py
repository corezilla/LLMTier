"""Case ID: AUTH-01

Endpoint: GET /v1/models
Upstream Provider: 无
Model: 无
Auth: 无（LAN trust）

断言：
- HTTP 200
- body 含 data[]
- 原因：客户端在 192.168.x RFC1918 LAN，LLMTIER_TRUSTED_LAN_MODE 默认开启
  （auth.py:33-34 unauthenticated_principal() 返回 trusted-lan-consumer）
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_auth_01_data_endpoint_no_token_lan_trust():
    """LAN trust case——不能复用 admin_client fixture（已带 token）。

    使用一个独立的 httpx 调用，不传 Authorization header。
    """
    import httpx
    with httpx.Client(base_url="http://192.168.1.9:8181", timeout=10.0) as client:
        resp = client.get("/v1/models")
    assert resp.status_code == 200, f"返回 {resp.status_code}（期望 200，LAN trust）: {resp.text}"
    body = resp.json()
    assert "data" in body
