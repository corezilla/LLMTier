"""Case ID: DP-RESP-02

Endpoint: POST /v1/responses (stream=false)
Upstream Provider: 无
Model: Worker
Auth: Bearer dev-data

断言：
- HTTP 400
- error.code == "unsupported_request"
- 原因：当前实现强制 stream=true（responses.py:50）
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_dp_resp_02_stream_false_rejected(api_client):
    resp = api_client.post(
        "/v1/responses",
        json={
            "model": "Worker",
            "input": [{"role": "user", "content": "Hello"}],
            "stream": False,
            "store": False,
        },
    )
    assert resp.status_code == 400, f"返回 {resp.status_code}（期望 400）: {resp.text}"
    body = resp.json()
    err = body.get("error") or {}
    assert err.get("code") == "unsupported_request", (
        f"error.code != 'unsupported_request': {err}"
    )
