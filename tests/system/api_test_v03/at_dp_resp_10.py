"""Case ID: DP-RESP-10

Endpoint: POST /v1/responses
Upstream Provider: m5air OMLX (Qwen3.6)
Model: Worker
Auth: Bearer dev-data

目标：验证 max_output_tokens truncation 行为。

断言：
- HTTP 200
- SSE 序列终止于 response.incomplete（不是 response.completed）
- response.incomplete 中含 "incomplete_details": {"reason": "max_output_tokens"}

注：context_window 硬上限（262k tokens）在 Qwen3.6 上实测未触发 API 层错误；
真正可测的边界是 max_output_tokens truncation。
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_dp_resp_10_max_output_tokens_truncated(api_client):
    with api_client.stream(
        "POST",
        "/v1/responses",
        json={
            "model": "Worker",
            "input": [{"role": "user", "content": "Count from 1 to 1000. Output only numbers separated by commas."}],
            "stream": True,
            "store": False,
            "max_output_tokens": 10,
        },
    ) as resp:
        assert resp.status_code == 200
        from tests.system.api_test_v03.conftest import parse_sse_raw
        events = parse_sse_raw(resp)

    names = [e[0] for e in events]
    assert "response.created" in names
    incomplete_event = next((d for n, d in events if n == "response.incomplete"), None)
    assert incomplete_event is not None, f"缺 response.incomplete: {names}"

    incomplete = (incomplete_event.get("response") or {}).get("incomplete_details") or {}
    assert incomplete.get("reason") == "max_output_tokens", \
        f"期望 incomplete_details.reason=max_output_tokens，实际 {incomplete}"
