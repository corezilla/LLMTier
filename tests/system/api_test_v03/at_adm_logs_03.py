"""Case ID: ADM-LOGS-03

Endpoint: GET /v1/logs
Upstream Provider: 无
Model: 无
Auth: Bearer dev-data (data token, 不应授权 admin)

目标：观测/管理读面角色门——data 凭据访问 admin 读端点即 403（先于参数校验）。

断言：
- HTTP 403
- error.code == "permission_denied"
- error.type == "request_error"
- body 不含 LogPage 业务载荷
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_adm_logs_03_get_with_data_token(api_client):
    resp = api_client.get("/v1/logs")
    assert resp.status_code == 403, f"期望 403，实际 {resp.status_code}: {resp.text}"
    body = resp.json()
    err = body.get("error") or {}
    assert err.get("code") == "permission_denied", f"error.code != 'permission_denied': {err}"
    assert err.get("type") == "request_error", f"error.type != 'request_error': {err}"
    assert "data" not in body, f"拒绝路径不得泄露 LogPage 载荷: {body}"
