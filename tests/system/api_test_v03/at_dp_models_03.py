"""Case ID: DP-MODELS-03

Endpoint: GET /v1/models/worker（小写）
Upstream Provider: 无
Model: 无
Auth: Bearer dev-data

断言：
- HTTP 404
- error.code == "model_not_found"
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_dp_models_03_lowercase_rejected(api_client):
    resp = api_client.get("/v1/models/worker")
    assert resp.status_code == 404, f"返回 {resp.status_code}（期望 404）: {resp.text}"
    body = resp.json()
    err = body.get("error") or {}
    assert err.get("code") == "model_not_found", f"error.code != 'model_not_found': {err}"
