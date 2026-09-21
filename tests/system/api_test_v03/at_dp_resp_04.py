"""Case ID: DP-RESP-04

Endpoint: POST /v1/responses (tools 透传)
Upstream Provider: 调度器选
Model: Worker
Auth: Bearer dev-data

断言：
- HTTP 200，SSE 完整
- 不断言是否出现 function_call_arguments 事件（上游行为，不是 LLMTier 契约）

注：本 case 验证 LLMTier 接受合法 tools 参数并透传，不验证上游是否调用工具。
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_dp_resp_04_tools_passed_through(api_client):
    resp = api_client.post(
        "/v1/responses",
        json={
            "model": "Worker",
            "input": [{"role": "user", "content": "What's the weather in SF?"}],
            "stream": True,
            "store": False,
            "tools": [
                {
                    "type": "function",
                    "name": "get_weather",
                    "description": "Get current weather",
                    "parameters": {
                        "type": "object",
                        "properties": {"location": {"type": "string"}},
                        "required": ["location"],
                    },
                }
            ],
            "max_output_tokens": 100,
        },
    )
    # 同步请求会等 SSE 完整收完
    assert resp.status_code == 200, f"status {resp.status_code}: {resp.text}"
    body_text = resp.text
    assert "response.created" in body_text, "缺 response.created"
    assert "response.completed" in body_text, "缺 response.completed"
