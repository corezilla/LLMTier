"""Case ID: DP-EMB-04

Endpoint: POST /v1/embeddings (unknown model)
Upstream Provider: 无
Model: NonExistentModel
Auth: Bearer dev-data

断言：
- HTTP 404
- error.code == "not_found"（service-level 找不到；区别于 /v1/responses 的 model_not_found）
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_dp_emb_04_unknown_model(api_client):
    resp = api_client.post(
        "/v1/embeddings",
        json={"model": "NonExistentModel", "input": "hello"},
    )
    assert resp.status_code == 404, f"返回 {resp.status_code}（期望 404）: {resp.text}"
    body = resp.json()
    err = body.get("error") or {}
    assert err.get("code") == "not_found", f"error.code != 'not_found': {err}"
