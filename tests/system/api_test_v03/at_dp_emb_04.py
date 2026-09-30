"""Case ID: DP-EMB-04

Endpoint: POST /v1/embeddings (unknown model)
Upstream Provider: 无
Model: NonExistentModel
Auth: Bearer dev-data

断言：
- HTTP 404；Content-Type: application/json（非成功体）
- error 键集恰 5 键 {message,type,code,param,retryable}（无 category）
- error.code == "model_not_found"、type == "request_error"、param is None、retryable is False

注：registry.get_service_level 抛 404 not_found；EmbeddingsService.create 捕获该
404 并 remap 为 404 model_not_found（src/inference/embeddings.py:36-39）。
"""
from __future__ import annotations

from tests.system.api_test_v03.conftest import error_envelope

import pytest


@pytest.mark.api_a
def test_dp_emb_04_unknown_model(api_client):
    resp = api_client.post(
        "/v1/embeddings",
        json={"model": "NonExistentModel", "input": "hello"},
    )
    assert resp.status_code == 404, f"返回 {resp.status_code}（期望 404）: {resp.text}"
    assert resp.headers.get("content-type", "").startswith("application/json")
    body = resp.json()
    assert "data" not in body and "object" not in body, (
        f"错误响应不得含成功字段: {sorted(body.keys())}"
    )

    err = error_envelope(resp)
    assert err["code"] == "model_not_found", f"error.code != 'model_not_found': {err}"
    assert err["type"] == "request_error", f"error.type != 'request_error': {err}"
    assert err["param"] is None, f"error.param 非 null: {err}"
    assert err["retryable"] is False, f"error.retryable 非 False: {err}"
