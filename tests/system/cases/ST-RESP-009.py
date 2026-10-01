"""Case ID: ST-RESP-009

Endpoint: POST /v1/responses (previous_response_id)
Upstream Provider: 无
Model: Worker
Auth: Bearer dev-data

断言：
- HTTP 400；Content-Type: application/json（非 SSE）
- error 键集恰 5 键 {message,type,code,param,retryable}（无 category）
- error.code == "unsupported_field"、type == "request_error"、param == "previous_response_id"、retryable is False

注：FORBIDDEN_FIELDS 检查先于 ALLOWED_FIELDS，故本 case 观测 unsupported_field；系统 §7.8 ERR-REQ-FIELD 要求 param=未知字段名。
"""
from __future__ import annotations

from tests.system.conftest import error_envelope

import pytest


@pytest.mark.api_a
def test_dp_resp_09_previous_response_id_rejected(api_client):
    resp = api_client.post(
        "/v1/responses",
        json={
            "model": "Worker",
            "input": [{"role": "user", "content": "hi"}],
            "stream": True,
            "store": False,
            "previous_response_id": "resp_xxx",
        },
    )
    assert resp.status_code == 400, f"返回 {resp.status_code}（期望 400）: {resp.text}"
    ct = resp.headers.get("content-type", "")
    assert ct.startswith("application/json"), f"错误响应应 JSON（非 SSE）: {ct!r}"

    err = error_envelope(resp)
    assert err["code"] == "unsupported_field", f"error.code != 'unsupported_field': {err}"
    assert err["type"] == "request_error", f"error.type != 'request_error': {err}"
    assert err["param"] == "previous_response_id", f"error.param != 'previous_response_id': {err}"
    assert err["retryable"] is False, f"error.retryable 非 False: {err}"
