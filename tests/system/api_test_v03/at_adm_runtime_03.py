"""Case ID: ADM-RUNTIME-03

Endpoint: GET /v1/runtime
Upstream Provider: 无
Model: 无
Auth: Authorization: Basic ZGV2LWRhdGE= (非法授权方案，非 Bearer)

目标：缺凭据/非法方案判定路径——受保护端点 + 非 Bearer 方案 ⇒ 401。

构造诚实性：源码对 loopback/RFC1918 且无 Authorization 头无条件授权，
无法构造"完全无头"的 401；故以非法方案（Basic）触发同一 401 分支。

断言：
- HTTP 401（不是 403，也不是 200）
- error.code == "authentication_required"
- error.type == "request_error"
- body 不含运行态快照字段
"""
from __future__ import annotations

import httpx
import pytest


@pytest.mark.api_a
def test_adm_runtime_03_invalid_auth_scheme(m5air_base_url):
    with httpx.Client(base_url=m5air_base_url, timeout=10.0) as client:
        resp = client.get("/v1/runtime", headers={"Authorization": "Basic ZGV2LWRhdGE="})
    assert resp.status_code == 401, f"期望 401，实际 {resp.status_code}: {resp.text}"
    body = resp.json()
    err = body.get("error") or {}
    assert err.get("code") == "authentication_required", f"error.code != 'authentication_required': {err}"
    assert err.get("type") == "request_error", f"error.type != 'request_error': {err}"
    for field in ("deployments", "providers", "queues"):
        assert field not in body, f"拒绝路径不得泄露运行态字段 {field}: {body}"
