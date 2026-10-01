"""Case ID: ST-auth-005

Endpoint: GET /healthz
Upstream Provider: 无
Model: 无
Auth: 无

断言：
- HTTP 200
- body.status == "ok"
- 证据：裸客户端未发送 Authorization 头（证明公共端点免凭据，而非"带 token 也 200"）
- 公共端点不需要任何 auth（app.py:196 在 _dispatch 最前短路，不调 self._auth()）
"""
from __future__ import annotations

import httpx
import pytest


@pytest.mark.api_a
def test_auth_05_public_endpoint_no_token():
    with httpx.Client(base_url="http://192.168.1.9:8181", timeout=10.0) as client:
        assert "authorization" not in {k.lower() for k in client.headers}, (
            f"裸客户端不应携带 Authorization 头: {dict(client.headers)}"
        )
        resp = client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("status") == "ok"
