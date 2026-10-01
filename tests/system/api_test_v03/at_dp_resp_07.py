"""Case ID: ST-resp-007

Endpoint: POST /v1/responses (store=true)
Upstream Provider: 无
Model: Worker
Auth: Bearer dev-data

断言：
- HTTP 400；Content-Type: application/json（非 SSE）
- error 键集恰 5 键 {message,type,code,param,retryable}（无 category）
- error.code == "unsupported_request"、type == "request_error"、param is None、retryable is False
"""
from __future__ import annotations

from tests.system.api_test_v03.conftest import error_envelope

import pytest


@pytest.mark.api_a
def test_dp_resp_07_store_true_rejected(api_client):
    resp = api_client.post(
        "/v1/responses",
        json={
            "model": "Worker",
            "input": [{"role": "user", "content": "hi"}],
            "stream": True,
            "store": True,
        },
    )
    assert resp.status_code == 400, f"返回 {resp.status_code}（期望 400）: {resp.text}"
    ct = resp.headers.get("content-type", "")
    assert ct.startswith("application/json"), f"错误响应应 JSON（非 SSE）: {ct!r}"

    err = error_envelope(resp)
    assert err["code"] == "unsupported_request", f"error.code != 'unsupported_request': {err}"
    assert err["type"] == "request_error", f"error.type != 'request_error': {err}"
    assert err["param"] is None, f"error.param 非 null: {err}"
    assert err["retryable"] is False, f"error.retryable 非 False: {err}"
