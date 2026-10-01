"""Case ID: ST-RESP-008

Endpoint: POST /v1/responses (missing model)
Upstream Provider: 无
Model: 无
Auth: Bearer dev-data

断言：
- HTTP 400；Content-Type: application/json（非 SSE）
- error 键集恰 5 键 {message,type,code,param,retryable}（无 category）
- error.code == "invalid_request"、type == "request_error"、retryable is False
- error.param == "model"（清单/OpenAPI ResponsesRequest.required；responses.py:72-73 传入缺失字段名）
"""
from __future__ import annotations

from tests.system.conftest import error_envelope

import pytest


@pytest.mark.api_a
def test_dp_resp_08_missing_model(api_client):
    resp = api_client.post(
        "/v1/responses",
        json={
            "input": [{"role": "user", "content": "hi"}],
            "stream": True,
            "store": False,
        },
    )
    assert resp.status_code == 400, f"返回 {resp.status_code}（期望 400）: {resp.text}"
    ct = resp.headers.get("content-type", "")
    assert ct.startswith("application/json"), f"错误响应应 JSON（非 SSE）: {ct!r}"

    err = error_envelope(resp)
    assert err["code"] == "invalid_request", f"error.code != 'invalid_request': {err}"
    assert err["type"] == "request_error", f"error.type != 'request_error': {err}"
    assert err["retryable"] is False, f"error.retryable 非 False: {err}"
    assert err["param"] == "model", f"error.param != 'model': {err}"
