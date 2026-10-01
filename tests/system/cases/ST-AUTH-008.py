"""Case ID: ST-AUTH-008

Endpoint: GET /tier/admin/v1/diagnostics
Upstream Provider: 无
Model: 无
Auth: Bearer dev-data（data token，别名命名空间要求 admin）

依赖（TS-002）：
  Endpoint: http://192.168.1.9:8181（m5air A 类实例）
  Auth: Bearer dev-data
  上游: 无（本 case 不触发上游）

断言（ST-AUTH-008）：
- HTTP 403（别名命名空间 /tier/admin/v1/* 与扁平 /v1/* 同样要求 admin）
- error.code == "permission_denied"，error.type == "request_error"，
  error.param is None，error.retryable is False，error 恰 5 键
- body 不含 SwitchState 字段（snapshots_enabled/stats_enabled），拒绝路径不泄露诊断开关

注：app.py:248 principal = self._auth("admin") 位于所有 /tier/admin/v1/* 别名分支
（app.py:348 起）之前；data token 不匹配 admin role ⇒ 403，早于别名 handler。
"""
from __future__ import annotations

import httpx
import pytest


@pytest.mark.api_a
def test_auth_08_alias_namespace_requires_admin():
    with httpx.Client(base_url="http://192.168.1.9:8181", timeout=10.0) as client:
        resp = client.get(
            "/tier/admin/v1/diagnostics",
            headers={"Authorization": "Bearer dev-data"},
        )
    assert resp.status_code == 403, (
        f"返回 {resp.status_code}（期望 403，别名命名空间要求 admin）: {resp.text}"
    )
    body = resp.json()
    assert set(body.keys()) == {"error"}, f"envelope must have exactly one 'error' key: {body}"
    err = body["error"]
    assert set(err.keys()) == {"message", "type", "code", "param", "retryable"}, (
        f"error envelope must have exactly 5 keys: {sorted(err.keys())}"
    )
    assert err["code"] == "permission_denied", f"error.code != 'permission_denied': {err}"
    assert err["type"] == "request_error", f"error.type != 'request_error': {err}"
    assert err["param"] is None, f"error.param != None: {err}"
    assert err["retryable"] is False, f"error.retryable != False: {err}"

    # 拒绝路径不得泄露诊断开关（SwitchState 字段）。
    assert "snapshots_enabled" not in body and "stats_enabled" not in body, (
        f"403 body 不得泄露 SwitchState 字段: {body}"
    )
