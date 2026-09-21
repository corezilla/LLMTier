"""Case ID: AUTH-07

Endpoint: GET /v1/models (no token scenario)
Upstream Provider: 无
Model: 无
Auth: 无 (DEV_MODE=0, 无 LLMTIER_AUTH_TOKENS)

目标：验证 auth 未配置时 → 503 auth_not_configured。

断言：
- HTTP 503
- error.code == "auth_not_configured"
"""
from __future__ import annotations

import pytest


@pytest.mark.api_b
def test_auth_07_no_auth_configured(admin_client_b_no_auth):
    resp = admin_client_b_no_auth.get("/v1/models")
    assert resp.status_code == 503, f"期望 503，实际 {resp.status_code}: {resp.text}"
    err = resp.json().get("error") or {}
    assert err.get("code") == "auth_not_configured"
