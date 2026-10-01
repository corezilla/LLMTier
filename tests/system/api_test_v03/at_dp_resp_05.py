"""Case ID: ST-RESP-005

Endpoint: POST /v1/responses (unknown model)
Upstream Provider: 无
Model: NonExistentModel
Auth: Bearer dev-data

断言：
- HTTP 404；Content-Type: application/json（非 SSE）
- error 键集恰 5 键 {message,type,code,param,retryable}（无 category）
- error.code == "model_not_found"、type == "request_error"、param is None、retryable is False

注：model 不在 7 个 FIXED_TIERS 时 registry.get_service_level 先抛 404 not_found；
ResponsesService.create 捕获该 404 并 remap 为 404 model_not_found
（src/inference/responses.py:80-83）。
"""
from __future__ import annotations

from tests.system.api_test_v03.conftest import error_envelope

import pytest


@pytest.mark.api_a
def test_dp_resp_05_unknown_model(api_client):
    resp = api_client.post(
        "/v1/responses",
        json={
            "model": "NonExistentModel",
            "input": [{"role": "user", "content": "hi"}],
            "stream": True,
            "store": False,
        },
    )
    assert resp.status_code == 404, f"返回 {resp.status_code}（期望 404）: {resp.text}"
    ct = resp.headers.get("content-type", "")
    assert ct.startswith("application/json"), f"错误响应应 JSON（非 SSE）: {ct!r}"

    err = error_envelope(resp)
    assert err["code"] == "model_not_found", f"error.code != 'model_not_found': {err}"
    assert err["type"] == "request_error", f"error.type != 'request_error': {err}"
    assert err["param"] is None, f"error.param 非 null: {err}"
    assert err["retryable"] is False, f"error.retryable 非 False: {err}"
