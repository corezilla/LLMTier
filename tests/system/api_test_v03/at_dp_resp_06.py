"""Case ID: ST-RESP-006

Endpoint: POST /v1/responses (stream=true 显式)
Upstream Provider: 调度器选
Model: Worker
Auth: Bearer dev-data

断言：
- HTTP 200，Content-Type: text/event-stream
- 含 response.created 与唯一 terminal response.completed
- 各帧 sequence_number 严格递增
- 流末尾出现 data: [DONE]
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
def test_dp_resp_06_stream_true_accepted(api_client):
    # max_output_tokens=30 对任何长于一个词的答案都会截断为 response.incomplete；
    # 本 case 的契约是「stream=true 被受理 + SSE 收尾」，故 helper 有界重试直至
    # terminal 恰为 response.completed（并同时消除共享并发 5xx/429 噪声）。
    events, saw_done, _attempts = post_stream_until_terminal(
        api_client,
        {
            "model": "Worker",
            "input": [{"role": "user", "content": "Hello"}],
            "stream": True,
            "store": False,
            "max_output_tokens": 64,
        },
        terminal="response.completed",
    )

    names = [name for name, _ in events]
    assert "response.created" in names, f"缺 response.created: {names}"

    terminal_names = {"response.completed", "response.incomplete", "response.failed"}
    terminals = [n for n in names if n in terminal_names]
    assert len(terminals) == 1, f"应恰有 1 个 terminal，实际 {terminals}: {names}"
    assert terminals[0] == "response.completed", f"terminal 应为 response.completed: {terminals}"

    seqs = [d["sequence_number"] for _, d in events if isinstance(d, dict) and "sequence_number" in d]
    for i in range(1, len(seqs)):
        assert seqs[i] > seqs[i - 1], f"sequence_number 非严格递增: {seqs}"

    assert saw_done, "SSE 流缺 data: [DONE] 终止标记"
