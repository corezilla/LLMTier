"""Case ID: DP-EMB-04

Endpoint: POST /v1/embeddings (unknown model)
Upstream Provider: 无
Model: NonExistentModel
Auth: Bearer dev-data

断言：
- HTTP 404
- error.code == "model_not_found"

注：registry.get_service_level 抛 404 not_found；EmbeddingsService.create 捕获该
404 并 remap 为 404 model_not_found（src/inference/embeddings.py:36-39）。
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
    assert err.get("code") == "model_not_found", f"error.code != 'model_not_found': {err}"
