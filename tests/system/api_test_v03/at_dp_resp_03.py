"""Case ID: DP-RESP-03

Endpoint: POST /v1/responses (推理 prompt)
Upstream Provider: 调度器选
Model: Worker
Auth: Bearer dev-data

断言：
- HTTP 200，SSE 完整
- 收集所有 output_text.delta 文本，断言含 "390"（最终结果）且含 "15" 和 "23"（输入数字）

注：上游是 gemma-4-e2b-it-4bit (本地 OMLX)。gemma 可能把推理步骤内嵌在
output_text 而非独立 reasoning_text 事件——本 case 只断言 output_text 内容。
"""
from __future__ import annotations

import json

import pytest


def _parse_sse_text(resp) -> str:
    full = ""
    event_name = None
    data_buf: list[str] = []
    for raw in resp.iter_lines():
        if raw is None:
            continue
        line = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
        if line.startswith("event:"):
            event_name = line[len("event:"):].strip()
        elif line.startswith("data:"):
            data_buf.append(line[len("data:"):].strip())
        elif line == "":
            if event_name == "response.output_text.delta" and data_buf:
                try:
                    payload = json.loads("\n".join(data_buf))
                except json.JSONDecodeError:
                    payload = {}
                full += payload.get("delta", "")
            event_name = None
            data_buf = []
    return full


@pytest.mark.api_a
def test_dp_resp_03_reasoning_contains_390(api_client):
    with api_client.stream(
        "POST",
        "/v1/responses",
        json={
            "model": "Worker",
            "input": [{"role": "user", "content": "Calculate 15 * 23 + 45 step by step"}],
            "stream": True,
            "store": False,
            "max_output_tokens": 200,
        },
    ) as resp:
        assert resp.status_code == 200, f"status {resp.status_code}: {resp.text}"
        text = _parse_sse_text(resp)

    assert text, "output_text 为空"
    assert "390" in text, f"output_text 缺 '390': {text[:200]!r}"
    assert "15" in text, f"output_text 缺 '15': {text[:200]!r}"
    assert "23" in text, f"output_text 缺 '23': {text[:200]!r}"
