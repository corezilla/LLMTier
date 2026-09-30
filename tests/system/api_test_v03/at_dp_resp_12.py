"""Case ID: DP-RESP-12

Endpoint: POST /v1/responses
Upstream Provider: 无
Model: Worker
Auth: Bearer dev-data

目标：conversation_id 不在 ResponsesRequest/ALLOWED_FIELDS 中（additionalProperties:false），
被 dispatch 前的未知字段校验拒绝。

断言：
- HTTP 400；Content-Type: application/json（非 SSE）
- error 键集恰 5 键 {message,type,code,param,retryable}
- error.code == "unsupported_field"、type == "request_error"、param == "conversation_id"、retryable is False
- error.message 含 "unknown fields"
- 对照：去掉 conversation_id 的同一请求应 200 + SSE（隔离归因）
"""
from __future__ import annotations

from tests.system.api_test_v03.conftest import error_envelope, request_with_retry

import pytest

BASE_BODY = {
    "model": "Worker",
    "input": [{"role": "user", "content": "hi"}],
    "stream": True,
    "store": False,
}


@pytest.mark.api_a
def test_dp_resp_12_conversation_id_rejected(api_client):
    resp = api_client.post(
        "/v1/responses",
        json={**BASE_BODY, "conversation_id": "conv_ignored_test"},
    )
    assert resp.status_code == 400, f"期望 400，实际 {resp.status_code}: {resp.text}"
    ct = resp.headers.get("content-type", "")
    assert ct.startswith("application/json"), f"错误响应应 JSON（非 SSE）: {ct!r}"

    err = error_envelope(resp)
    assert err["code"] == "unsupported_field", f"error.code != 'unsupported_field': {err}"
    assert err["type"] == "request_error", f"error.type != 'request_error': {err}"
    assert err["param"] == "conversation_id", f"error.param != 'conversation_id': {err}"
    assert err["retryable"] is False, f"error.retryable 非 False: {err}"
    assert "unknown fields" in err["message"], f"message 未含 'unknown fields': {err}"

    # 对照（隔离归因）：去掉越界字段后应受理（200 + SSE）。
    control = request_with_retry(api_client, "POST", "/v1/responses", json=BASE_BODY)
    assert control.status_code == 200, (
        f"去掉 conversation_id 后应受理，实际 {control.status_code}: {control.text[:200]}"
    )
    assert control.headers.get("content-type", "").startswith("text/event-stream"), (
        f"对照应返回 SSE: {control.headers.get('content-type')!r}"
    )
