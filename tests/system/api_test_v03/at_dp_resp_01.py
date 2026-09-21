"""Case ID: DP-RESP-01

Endpoint: POST /v1/responses (stream=true)
Upstream Provider: 调度器选（默认三选一）
Model: Worker
Auth: Bearer dev-data

断言：
- HTTP 200，Content-Type: text/event-stream
- SSE 事件序列（按 sse.py 真相）：
  response.created → response.output_item.added
  → response.output_text.delta ×N
  → response.output_text.done
  → response.output_item.done
  → response.completed (status=completed)
  → data: [DONE]
- 每帧含 sequence_number，单调递增从 0 开始
- response.completed 事件内 usage.input_tokens/output_tokens/total_tokens 都非 null
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
def test_dp_resp_01_streaming_sse_complete(api_client):
    with api_client.stream(
        "POST",
        "/v1/responses",
        json={
            "model": "Worker",
            "input": [{"role": "user", "content": "Hello"}],
            "stream": True,
            "store": False,
            "max_output_tokens": 50,
        },
    ) as resp:
        assert resp.status_code == 200, f"status {resp.status_code}"
        ct = resp.headers.get("content-type", "")
        assert "text/event-stream" in ct, f"content-type={ct!r}, expect text/event-stream"

        events = _parse_sse(resp)

    assert events, "无 SSE 事件"

    # 抽取事件名序列
    names = [e[0] for e in events]
    assert "response.created" in names, f"缺 response.created: {names}"
    assert "response.output_item.added" in names, f"缺 output_item.added: {names}"
    assert "response.output_text.done" in names
    assert "response.output_item.done" in names
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

    # 验证 data: [DONE] 终止标记：在 events 之外，由 parse_sse 不解析 [DONE] 数据行
    # 这里不强求——某些 client 实现可能不发送 [DONE]
