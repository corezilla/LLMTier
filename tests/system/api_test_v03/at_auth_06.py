"""Case ID: AUTH-06

Endpoint: GET /v1/models
Upstream Provider: 无
Model: 无
Auth: "Bearer "（空 token，保留前缀）

断言：
- HTTP 403
- error.code == "permission_denied"
- **5 键信封 identity**（type/param/retryable 齐备）：type=="request_error"、retryable is False

注：auth.py:55-57，Bearer 后空字符串与 configured token 不匹配 → 403。
（区别于 auth.py:53 完全无 Authorization header 走 LAN trust。）

构造脆弱性登记（P2，当前正确）：`raw.startswith("Bearer ")` 依赖 header 保留
"Bearer " 的尾随空格。httpx 会规范化/拒绝该 header，故用 `urllib.request` 直连；
urllib 不发尾空格则 `startswith("Bearer ")` 变 False → 401 而非 403，本 case 会
假 FAIL。若未来更换客户端/代理（会 strip 尾空格），需改用能保留尾空格的原生
socket 构造。
"""
from __future__ import annotations

import json
import urllib.error
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
    assert set(body.keys()) == {"error"}, f"信封应恰含 error: {body}"
    err = body["error"]
    assert set(err.keys()) == {"message", "type", "code", "param", "retryable"}, (
        f"错误信封应恰 5 键: {sorted(err.keys())}"
    )
    assert err["code"] == "permission_denied", f"error.code != 'permission_denied': {err}"
    assert err["type"] == "request_error", f"error.type != 'request_error': {err}"
    assert err["retryable"] is False, f"error.retryable 应为 False: {err}"
