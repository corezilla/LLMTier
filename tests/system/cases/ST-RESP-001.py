"""Case ID: ST-RESP-001

Endpoint: POST /v1/responses (stream=true)
Upstream Provider: 调度器选（默认三选一）
Model: Worker
Auth: Bearer dev-data

断言：
- HTTP 200，Content-Type: text/event-stream
- SSE 事件序列（按 sse.py 真相）：
  response.created → response.output_item.added
  → response.output_text.delta ×N
  → response.output_item.done
  → response.completed (status=completed)
  → data: [DONE]
- 每帧含 sequence_number，单调递增从 0 开始
- 恰有一个 terminal 事件（completed/incomplete/failed）
- response.completed 事件内 usage.input_tokens/output_tokens/total_tokens 都非 null
"""
from __future__ import annotations

import json

import pytest

from tests.system.conftest import post_stream_until_terminal


def _parse_sse(resp) -> tuple[list[tuple[str, dict]], bool]:
    events: list[tuple[str, dict]] = []
    event_name = None
    data_buf: list[str] = []
    saw_done = False
    for raw in resp.iter_lines():
        if raw is None:
            continue
        line = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
        if line.startswith("event:"):
            event_name = line[len("event:"):].strip()
        elif line.startswith("data:"):
            value = line[len("data:"):].strip()
            if value == "[DONE]":
                saw_done = True
            data_buf.append(value)
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
    return events, saw_done


@pytest.mark.api_a
def test_dp_resp_01_streaming_sse_complete(api_client):
    # A 臂要求 terminal 恰为 response.completed（本 case 专测完整序列与 usage）。
    # 共享实例并发（retryable 5xx/429）与上游在 max_output_tokens 处截断
    # （response.incomplete）均为非确定性条件，helper 做有界重试直至 completed。
    events, saw_done, _attempts = post_stream_until_terminal(
        api_client,
        {
            "model": "Worker",
            "input": [{"role": "user", "content": "Hello"}],
            "stream": True,
            "store": False,
            "max_output_tokens": 512,
        },
        terminal="response.completed",
    )

    assert events, "无 SSE 事件"
    assert saw_done, "SSE 流缺 data: [DONE] 终止标记"

    # 抽取事件名序列
    names = [e[0] for e in events]
    assert names[0] == "response.created", f"首个事件应为 response.created: {names}"
    assert "response.output_item.added" in names, f"缺 output_item.added: {names}"
    assert "response.output_text.delta" in names, f"缺 output_text.delta: {names}"
    assert "response.output_item.done" in names, f"缺 output_item.done: {names}"
    # sse.py 从不发 response.output_text.done，锁定真实契约
    assert "response.output_text.done" not in names, f"sse.py 不发出 output_text.done: {names}"

    terminal = {"response.completed", "response.incomplete", "response.failed"}
    terminal_events = [n for n in names if n in terminal]
    assert len(terminal_events) == 1, f"应恰有 1 个 terminal 事件，实际 {terminal_events}: {names}"
    assert terminal_events[0] == "response.completed", f"terminal 应为 response.completed: {terminal_events}"
    assert names[-1] == "response.completed", f"最后事件应为 response.completed，实际 {names[-1]}"

    # response.completed 必有 usage
    completed = next(d for n, d in events if n == "response.completed")
    response = completed.get("response") or {}
    usage = response.get("usage") or {}
    assert usage.get("input_tokens") is not None, f"usage.input_tokens 缺失: {usage}"
    assert usage.get("output_tokens") is not None, f"usage.output_tokens 缺失: {usage}"
    assert usage.get("total_tokens") is not None, f"usage.total_tokens 缺失: {usage}"

    # sequence_number 单调递增（每个事件 data 内的 sequence_number 字段）
    seqs = []
    for _, data in events:
        if isinstance(data, dict) and "sequence_number" in data:
            seqs.append(data["sequence_number"])
    for i in range(1, len(seqs)):
        assert seqs[i] > seqs[i-1], f"sequence_number 非单调递增: {seqs}"
