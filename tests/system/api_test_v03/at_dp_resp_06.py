"""Case ID: DP-RESP-06

Endpoint: POST /v1/responses (stream=true 显式)
Upstream Provider: 调度器选
Model: Worker
Auth: Bearer dev-data

断言：
- HTTP 200，SSE 流式正常
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_dp_resp_06_stream_true_accepted(api_client):
    resp = api_client.post(
        "/v1/responses",
        json={
            "model": "Worker",
            "input": [{"role": "user", "content": "Hello"}],
            "stream": True,
            "store": False,
            "max_output_tokens": 30,
        },
    )
    assert resp.status_code == 200, f"status {resp.status_code}: {resp.text}"
    ct = resp.headers.get("content-type", "")
    assert "text/event-stream" in ct, f"content-type={ct!r}, expect text/event-stream"
    body = resp.text
    assert "response.completed" in body
