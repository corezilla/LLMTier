"""Case ID: DP-RESP-14

Endpoint: POST /v1/responses
Upstream Provider: m5air OMLX (Qwen3.6)
Model: Worker
Auth: Bearer dev-data

目标：验证 max_tokens 作为 max_output_tokens 别名被接受。

断言：
- HTTP 200
- 正常返回 SSE 流或 response 对象
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_dp_resp_14_max_tokens_alias(api_client):
    from tests.system.api_test_v03.conftest import parse_sse_raw

    with api_client.stream(
        "POST",
        "/v1/responses",
        json={
            "model": "Worker",
            "input": [{"role": "user", "content": "say hello"}],
            "stream": True,
            "store": False,
            "max_tokens": 50,
        },
    ) as resp:
        assert resp.status_code == 200, f"期望 200，实际 {resp.status_code}: {resp.text}"
        events = parse_sse_raw(resp)
    names = [e[0] for e in events]
    assert "response.created" in names, f"缺 response.created: {names}"
