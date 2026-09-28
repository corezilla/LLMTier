"""Case ID: DP-RESP-14

Endpoint: POST /v1/responses
Upstream Provider: m5air OMLX (Qwen3.6)
Model: Worker
Auth: Bearer dev-data

目标：max_tokens 不是 max_output_tokens 的别名，且不在 ResponsesRequest/
ALLOWED_FIELDS 中，被 dispatch 前的未知字段校验拒绝。

断言：
- HTTP 400
- error.code == "invalid_request"
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_dp_resp_14_max_tokens_rejected(api_client):
    resp = api_client.post(
        "/v1/responses",
        json={
            "model": "Worker",
            "input": [{"role": "user", "content": "say hello"}],
            "stream": True,
            "store": False,
            "max_tokens": 50,
        },
    )
    assert resp.status_code == 400, f"期望 400，实际 {resp.status_code}: {resp.text}"
    err = resp.json().get("error") or {}
    assert err.get("code") == "invalid_request", f"error.code != 'invalid_request': {err}"
