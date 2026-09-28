"""Case ID: DP-RESP-03

Endpoint: POST /v1/responses (推理 prompt)
Upstream Provider: 调度器选
Model: Worker
Auth: Bearer dev-data

断言（structure/events only — 不断言上游 LLM 的具体内容）：
- HTTP 200，Content-Type: text/event-stream
- 事件序列包含 response.created / response.output_text.delta
  / response.output_item.done / response.completed
  （sse.py 不发 response.output_text.done）
- 至少一个 output_text.delta 的 delta 是非空字符串
- response.completed 的 response.status == "completed"

注：上游模型输出格式不稳定，本 case 只验 LLMTier 的 SSE 契约，不把模型内容当 oracle。
"""
from __future__ import annotations

import json

import pytest


def _parse_sse(resp) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
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
            if event_name and data_buf:
                payload_str = "\n".join(data_buf)
                try:
                    payload = json.loads(payload_str)
                except json.JSONDecodeError:
                    payload = {"_raw": payload_str}
                events.append((event_name, payload))
            event_name = None
            data_buf = []
    return events


@pytest.mark.api_a
def test_dp_resp_03_streaming_structure(api_client):
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
        ct = resp.headers.get("content-type", "")
        assert "text/event-stream" in ct, f"content-type={ct!r}"
        events = _parse_sse(resp)

    assert events, "无 SSE 事件"
    names = [name for name, _ in events]
    for expected in (
        "response.created",
        "response.output_text.delta",
        "response.output_item.done",
    ):
        assert expected in names, f"缺事件 {expected}: {names}"
    assert "response.output_text.done" not in names, f"sse.py 不发出 output_text.done: {names}"

    deltas = [
        data.get("delta", "")
        for name, data in events
        if name == "response.output_text.delta"
    ]
    assert any(isinstance(delta, str) and delta for delta in deltas), f"无非空 delta: {deltas!r}"

    assert names[-1] == "response.completed", f"最后事件应为 response.completed，实际 {names[-1]}"
    completed = next(data for name, data in events if name == "response.completed")
    assert (completed.get("response") or {}).get("status") == "completed", f"status != completed: {completed}"
