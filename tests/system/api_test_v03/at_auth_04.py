"""Case ID: ST-auth-004

Endpoint: GET /v1/providers
Upstream Provider: 无
Model: 无
Auth: 无（LAN trust）

断言：
- HTTP 200
- body 含 data[]
- 证据：裸客户端未发送 Authorization 头
- 原因：客户端在 192.168.x RFC1918 LAN；auth.py:33-34 对 loopback 或 RFC1918/ULA
  地址**无条件**返回 trusted-lan-operator。**源码不读取 `LLMTIER_TRUSTED_LAN_MODE`**
  （auth.py 注释明示），该变量不参与鉴权判定。
"""
from __future__ import annotations

import httpx
import pytest


@pytest.mark.api_a
def test_auth_04_admin_endpoint_no_token_lan_trust():
    with httpx.Client(base_url="http://192.168.1.9:8181", timeout=10.0) as client:
        assert "authorization" not in {k.lower() for k in client.headers}, (
            f"裸客户端不应携带 Authorization 头: {dict(client.headers)}"
        )
        resp = client.get("/v1/providers")
    assert resp.status_code == 200, f"返回 {resp.status_code}（期望 200，LAN trust）: {resp.text}"
    body = resp.json()
    assert "data" in body
