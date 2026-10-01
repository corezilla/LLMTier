"""Case ID: ST-RUNTIME-003

Endpoint: GET /v1/runtime
Upstream Provider: 无
Model: 无
Auth: Authorization: Basic ZGV2LWRhdGE= (非法授权方案，非 Bearer)

目标：缺凭据/非法方案判定路径——受保护端点 + 非 Bearer 方案 ⇒ 401。

构造诚实性：源码对 loopback/RFC1918 且无 Authorization 头无条件授权，
无法构造"完全无头"的 401；故以非法方案（Basic）触发同一 401 分支。

断言（doc §4 步 5）：
- HTTP 401（不是 403，也不是 200）
- error 信封恰 5 键；code == "authentication_required"、type == "request_error"、
  param is None、retryable is False
- body 不含运行态快照字段
"""
from __future__ import annotations

import httpx
import pytest

from tests.system.api_test_v03.conftest import error_envelope


@pytest.mark.api_a
def test_adm_runtime_03_invalid_auth_scheme(m5air_base_url):
    with httpx.Client(base_url=m5air_base_url, timeout=10.0) as client:
        resp = client.get("/v1/runtime", headers={"Authorization": "Basic ZGV2LWRhdGE="})
    assert resp.status_code == 401, f"期望 401，实际 {resp.status_code}: {resp.text}"
    err = error_envelope(resp)
    assert err["code"] == "authentication_required", f"error.code != 'authentication_required': {err}"
    assert err["type"] == "request_error", f"error.type != 'request_error': {err}"
    assert err["param"] is None, f"error.param != None: {err}"
    assert err["retryable"] is False, f"error.retryable != False: {err}"
    body = resp.json()
    for field in ("deployments", "providers", "queues"):
        assert field not in body, f"拒绝路径不得泄露运行态字段 {field}: {body}"
