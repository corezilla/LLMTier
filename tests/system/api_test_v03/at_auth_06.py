"""Case ID: AUTH-06

Endpoint: GET /v1/models
Upstream Provider: 无
Model: 无
Auth: "Bearer "（空 token，保留前缀）

断言：
- HTTP 403
- error.code == "permission_denied"

注：auth.py:55-57，Bearer 后空字符串与 configured token 不匹配 → 403。
（区别于 auth.py:53 完全无 Authorization header 走 LAN trust。）

httpx 不允许发 "Bearer "（空 Bearer）这种 header，所以用 urllib 直连。
"""
from __future__ import annotations

import json
import urllib.request

import pytest


@pytest.mark.api_a
def test_auth_06_empty_bearer_token():
    req = urllib.request.Request(
        "http://192.168.1.9:8181/v1/models",
        headers={"Authorization": "Bearer "},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            body_text = resp.read().decode()
    except urllib.error.HTTPError as e:
        status = e.code
        body_text = e.read().decode()

    assert status == 403, f"返回 {status}（期望 403）: {body_text}"
    body = json.loads(body_text)
    err = body.get("error") or {}
    assert err.get("code") == "permission_denied", f"error.code != 'permission_denied': {err}"
