"""Case ID: DP-RESP-15

Endpoint: POST /v1/responses
Upstream Provider: m5air OMLX (Qwen3.6)
Model: Worker
Auth: Bearer dev-data

目标：temperature 是合法可选字段（被受理）；top_p 不在 ResponsesRequest/
ALLOWED_FIELDS 中，出现即触发未知字段拒绝。

断言：
- (a) 仅 temperature：HTTP 200，Content-Type text/event-stream，含 response.completed
- (b) temperature + top_p：HTTP 400，application/json（非 SSE）；
  error 键集恰 5 键、code=="unsupported_field"、type=="request_error"、param=="top_p"、
  retryable is False、message 含 "unknown fields"
"""
from __future__ import annotations

from tests.system.api_test_v03.conftest import (
    error_envelope,
    post_stream_until_terminal,
)

import pytest


@pytest.mark.api_a
def test_dp_resp_15_temperature_top_p(api_client):
    accepted_body = {
        "model": "Worker",
        "input": [{"role": "user", "content": "say hello"}],
        "stream": True,
        "store": False,
        "temperature": 0.7,
        "max_output_tokens": 256,
    }
    # 受理 + SSE 收尾；helper 对共享并发（5xx/429）与上游截断（incomplete）有界重试。
    events, _saw_done, _attempts = post_stream_until_terminal(
        api_client, accepted_body, terminal="response.completed"
    )
    names = [name for name, _ in events]
    assert "response.completed" in names, f"缺 response.completed: {names}"

    resp = api_client.post(
        "/v1/responses",
        json={**accepted_body, "top_p": 0.9},
    )
    assert resp.status_code == 400, f"期望 400，实际 {resp.status_code}: {resp.text}"
    ct = resp.headers.get("content-type", "")
    assert ct.startswith("application/json"), f"错误响应应 JSON（非 SSE）: {ct!r}"

    err = error_envelope(resp)
    assert err["code"] == "unsupported_field", f"error.code != 'unsupported_field': {err}"
    assert err["type"] == "request_error", f"error.type != 'request_error': {err}"
    assert err["param"] == "top_p", f"error.param != 'top_p': {err}"
    assert err["retryable"] is False, f"error.retryable 非 False: {err}"
    assert "unknown fields" in err["message"], f"message 未含 'unknown fields': {err}"
