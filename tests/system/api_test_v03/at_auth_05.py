"""Case ID: AUTH-05

Endpoint: GET /healthz
Upstream Provider: 无
Model: 无
Auth: 无

断言：
- HTTP 200
- body.status == "ok"
- 公共端点不需要任何 auth（app.py 不调 self._auth()）
"""
from __future__ import annotations

import httpx
import pytest


@pytest.mark.api_a
def test_auth_05_public_endpoint_no_token():
    with httpx.Client(base_url="http://192.168.1.9:8181", timeout=10.0) as client:
        resp = client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("status") == "ok"
