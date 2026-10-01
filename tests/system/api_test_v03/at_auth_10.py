"""Case ID: ST-auth-010

Endpoint: GET /v1/models
Upstream Provider: 无
Model: 无
Auth: Authorization: Basic ZGV2LWRhdGE=（非法授权方案）

依赖（TS-002）：
  Endpoint: http://192.168.1.9:8181（m5air A 类实例）
  Auth: Basic 方案（非法）
  上游: 无

断言（ST-auth-010）：
- HTTP 401（非法方案 ≠ 凭据不匹配 403）
- error.code == "authentication_required"，error.type == "request_error"，
  error.param is None，error.retryable is False，error 恰 5 键
- body 不含 ModelList 载荷（object=="list"/data）

构造诚实性（如何触发）：本 case 契约有两半——(a)「无 Bearer 且不命中免登录」、(b)「非法
授权方案」。在 A/B 两班**均无法构造 (a)**：A 类执行机源地址为 RFC1918、B 类实例监听 loopback，
auth.py:33-34 的 unauthenticated_principal() 对 loopback/RFC1918 在完全无 Authorization 头时
**无条件**授予共享角色（不读 LLMTIER_TRUSTED_LAN_MODE），故"完全无头"恒为 200。非受信来源需
公网源地址，A/B 不可得。故本 case 以 **(b) 非法方案**（Authorization: Basic ...）触发 401——
它进入同一 authenticate() 的"非法方案"分支（auth.py:53-54），产出契约要求的 401；但不得据此
声称已验证 (a) 的"来源不受信"门。若伪造来源（X-Forwarded-For / 改 client_address / mock）
冒充 (a)，判 INVALID。
"""
from __future__ import annotations

import httpx
import pytest


@pytest.mark.api_a
def test_auth_10_illegal_scheme_401():
    # 不复用 api_client/admin_client（它们注入合法 bearer，会 200）。
    with httpx.Client(base_url="http://192.168.1.9:8181", timeout=10.0) as client:
        resp = client.get(
            "/v1/models",
            headers={"Authorization": "Basic ZGV2LWRhdGE="},
        )
    assert resp.status_code == 401, (
        f"返回 {resp.status_code}（期望 401，非法授权方案）: {resp.text}"
    )
    body = resp.json()
    assert set(body.keys()) == {"error"}, f"envelope must have exactly one 'error' key: {body}"
    err = body["error"]
    assert set(err.keys()) == {"message", "type", "code", "param", "retryable"}, (
        f"error envelope must have exactly 5 keys: {sorted(err.keys())}"
    )
    assert err["code"] == "authentication_required", (
        f"error.code != 'authentication_required': {err}"
    )
    assert err["type"] == "request_error", f"error.type != 'request_error': {err}"
    assert err["param"] is None, f"error.param != None: {err}"
    assert err["retryable"] is False, f"error.retryable != False: {err}"

    # 拒绝路径不得返回业务载荷。
    assert body.get("object") != "list", f"401 body 不得含 ModelList 字段 object: {body}"
    assert "data" not in body, f"401 body 不得含 ModelList 字段 data: {body}"
