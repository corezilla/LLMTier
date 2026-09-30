"""Case ID: ADM-DEPL-10

Endpoint: POST /v1/deployments
Upstream Provider: 无
Model: 无
Auth: Bearer dev-data (data token, 不应授权 admin)

目标：管理写面角色门——data 凭据访问 admin 写端点即 403。

断言：
- HTTP 403
- error.code == "permission_denied"
- error.type == "request_error"
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_adm_depl_10_post_with_data_token(api_client):
    body = {
        "id": "x",
        "name": "x",
        "provider_id": "provider_local",
        "backend_model": "m",
    }
    resp = api_client.post("/v1/deployments", json=body)
    assert resp.status_code == 403, f"期望 403，实际 {resp.status_code}: {resp.text}"
    err = resp.json().get("error") or {}
    assert err.get("code") == "permission_denied", f"error.code != 'permission_denied': {err}"
    assert err.get("type") == "request_error", f"error.type != 'request_error': {err}"
