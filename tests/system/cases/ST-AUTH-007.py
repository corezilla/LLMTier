"""Case ID: ST-AUTH-007

Endpoint: GET /v1/models (no token scenario)
Upstream Provider: 无
Model: 无
Auth: 无 (DEV_MODE=0, 无 LLMTIER_AUTH_TOKENS)

目标：验证 auth 未配置时 → 503 auth_not_configured。

断言：
- HTTP 503
- error.code == "auth_not_configured"
- **5 键信封 identity**：type=="server_error"（503≥500）、retryable is False
- **不得夹带 ModelList 业务载荷**（无 data / object=="list"）
"""
from __future__ import annotations

import pytest


@pytest.mark.api_b
def test_auth_07_no_auth_configured(admin_client_b_no_auth):
    resp = admin_client_b_no_auth.get("/v1/models")
    assert resp.status_code == 503, f"期望 503，实际 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert set(body.keys()) == {"error"}, f"503 信封应恰含 error: {body}"
    err = body["error"]
    assert set(err.keys()) == {"message", "type", "code", "param", "retryable"}, (
        f"错误信封应恰 5 键: {sorted(err.keys())}"
    )
    assert err["code"] == "auth_not_configured", f"error.code != 'auth_not_configured': {err}"
    assert err["type"] == "server_error", f"503 的 error.type 应为 server_error: {err}"
    assert err["retryable"] is False, f"error.retryable 应为 False: {err}"
    assert "data" not in body, f"503 不得夹带 ModelList 载荷: {body}"
    assert body.get("object") != "list", f"503 不得夹带 ModelList 载荷: {body}"
