"""Case ID: ST-resp-003

Endpoint: POST /v1/responses (推理 prompt)
Upstream Provider: 调度器选
Model: Worker
Auth: Bearer dev-data

断言（structure/events only — 不断言上游 LLM 的具体内容）：
- HTTP 200，Content-Type: text/event-stream
- 事件序列包含 response.created / response.output_text.delta
  / response.output_item.done / response.completed
  （sse.py 不发 response.output_text.done）
- 恰一个 terminal（completed/incomplete/failed），且为 response.completed
- response.completed 的 response.status == "completed"
- 各帧 sequence_number 严格递增
- 流末尾出现 data: [DONE]

注：上游模型输出格式不稳定，本 case 只验 LLMTier 的 SSE 契约，不把模型内容当 oracle。
"""
from __future__ import annotations

import json

import pytest

from tests.system.api_test_v03.conftest import post_stream_until_terminal


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
def test_dp_resp_03_streaming_structure(api_client):
    # 本 case 要求 terminal 恰为 response.completed（并断 status==completed）；
    # helper 对共享并发（retryable 5xx/429）与上游截断（incomplete）做有界重试。
    events, saw_done, _attempts = post_stream_until_terminal(
        api_client,
        {
            "model": "Worker",
            "input": [{"role": "user", "content": "Calculate 15 * 23 + 45 step by step"}],
            "stream": True,
            "store": False,
            "max_output_tokens": 1500,
        },
        terminal="response.completed",
    )

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

    # 恰一个 terminal，且为 completed（不是 incomplete/failed）。
    terminal_names = {"response.completed", "response.incomplete", "response.failed"}
    terminals = [n for n in names if n in terminal_names]
    assert len(terminals) == 1, f"应恰有 1 个 terminal，实际 {terminals}: {names}"
    assert terminals[0] == "response.completed", f"terminal 应为 response.completed: {terminals}"
    assert names[-1] == "response.completed", f"最后事件应为 response.completed，实际 {names[-1]}"

    completed = next(data for name, data in events if name == "response.completed")
    assert (completed.get("response") or {}).get("status") == "completed", f"status != completed: {completed}"

    # sequence_number 严格递增。
    seqs = [d["sequence_number"] for _, d in events if isinstance(d, dict) and "sequence_number" in d]
    for i in range(1, len(seqs)):
        assert seqs[i] > seqs[i - 1], f"sequence_number 非严格递增: {seqs}"

    assert saw_done, "SSE 流缺 data: [DONE] 终止标记"
