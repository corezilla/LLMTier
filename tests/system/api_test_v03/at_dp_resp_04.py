"""Case ID: DP-RESP-04

Endpoint: POST /v1/responses (tools 透传)
Upstream Provider: 调度器选（A 类）；LAN fake provider（B 类回声臂）
Model: Worker（A 类）；Senior→depl_b（B 类）
Auth: Bearer dev-data

执行门（强制，先于发请求）：经 GET /v1/models 确认所选 responses-capable tier 的
capabilities.tools == true；否则本臂 BLOCKED（能力前置不满足），不得静默 PASS、
不得降级为可选负向观测。

断言：
- (A 类) 能力门通过 e caps.tools==true 后：HTTP 200 + text/event-stream；
  唯一 terminal（completed 或 incomplete；不得为 failed）；sequence_number 递增；data: [DONE]
- (B 类，可证伪透传) 用 tools-capable B 实例 + fake provider 回声：携带 tools 与
  含 "CALL_TOOL" 的 prompt → 上游按收到的 tools[0].name 回传 function_call；
  SSE 的 response.output_item.done.item.type=="function_call" 且 name 等于所发工具名
  ⇒ 证明上游确实收到了 tools（透传）。

注：不把"上游是否调用工具"当 LLMTier 契约；B 类只把它作为**上游已收到 tools**的可证伪证据。
注：权威 Oracle 为 VRC-INF-001「SSE 事件子集 + terminal 唯一」。A 臂 terminal 允许
`response.completed` 或 `response.incomplete`（`max_output_tokens` 截断产生，属上游模型
非确定性，非网关契约破坏）；仅 `response.failed` 判失败。A 臂对 503/429（`retryable:true`
的上游不可用/准入背压）做有界重试，消除共享实例并发噪声。
"""
from __future__ import annotations

import json

import pytest

from tests.system.api_test_v03.conftest import send_stream_with_retry

TOOL = {
    "type": "function",
    "name": "get_weather",
    "description": "Get current weather",
    "parameters": {
        "type": "object",
        "properties": {"location": {"type": "string"}},
        "required": ["location"],
    },
}


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


def _tools_capable(api_client, model: str) -> bool:
    resp = api_client.get("/v1/models")
    assert resp.status_code == 200, f"/v1/models 返回 {resp.status_code}: {resp.text}"
    row = next((m for m in resp.json()["data"] if m["id"] == model), None)
    assert row is not None, f"{model} 不在 /v1/models 清单中"
    return (row.get("capabilities") or {}).get("tools") is True


@pytest.mark.api_a
def test_dp_resp_04_tools_accepted_a(api_client):
    # 执行门（强制）：能力前置不满足 → BLOCKED。
    if not _tools_capable(api_client, "Worker"):
        pytest.skip("BLOCKED (DP-RESP-04): Worker.capabilities.tools != true")

    resp = send_stream_with_retry(
        api_client,
        "POST",
        "/v1/responses",
        json={
            "model": "Worker",
            "input": [{"role": "user", "content": "What's the weather in SF?"}],
            "stream": True,
            "store": False,
            "tools": [TOOL],
            "max_output_tokens": 100,
        },
    )
    try:
        assert resp.status_code == 200, f"status {resp.status_code}: {resp.text}"
        ct = resp.headers.get("content-type", "")
        assert "text/event-stream" in ct, f"content-type={ct!r}, expect text/event-stream"
        events, saw_done = _parse_sse(resp)
    finally:
        resp.close()

    names = [name for name, _ in events]
    assert "response.created" in names, f"缺 response.created: {names}"
    terminal_names = {"response.completed", "response.incomplete", "response.failed"}
    terminals = [n for n in names if n in terminal_names]
    assert len(terminals) == 1, f"应恰有 1 个 terminal，实际 {terminals}: {names}"
    # Authoritative Oracle is VRC-INF-001: "SSE 事件子集 + terminal 唯一". A
    # successful, non-failure terminal may be `completed` OR `incomplete` — the
    # latter is returned when the upstream response is truncated at
    # `max_output_tokens` (a legitimate, non-deterministic property of the live
    # upstream model, not a gateway contract breach; this case does not test
    # upstream tool-call behavior per §1). Only `response.failed` is a failure.
    assert terminals[0] != "response.failed", (
        f"terminal 不得为 response.failed（唯一非失败 terminal 期望 completed/incomplete）: {terminals}"
    )

    seqs = [d["sequence_number"] for _, d in events if isinstance(d, dict) and "sequence_number" in d]
    for i in range(1, len(seqs)):
        assert seqs[i] > seqs[i - 1], f"sequence_number 非严格递增: {seqs}"
    assert saw_done, "SSE 流缺 data: [DONE]"


@pytest.mark.api_b
def test_dp_resp_04_tools_passthrough_echo_b(llmtier_b_tools):
    """Falsifiable passthrough: the upstream echoes the tool name it received."""
    client = llmtier_b_tools.api_client()
    try:
        # 执行门：B 实例必须声明 tools=true（否则 construct 错）。
        caps = client.get("/v1/models")
        assert caps.status_code == 200, f"/v1/models 返回 {caps.status_code}: {caps.text}"
        row = next((m for m in caps.json()["data"] if m["id"] == "Senior"), None)
        assert row is not None and (row.get("capabilities") or {}).get("tools") is True, (
            f"B 实例 Senior.capabilities.tools 应为 true: {row}"
        )

        with client.stream(
            "POST",
            "/v1/responses",
            json={
                "model": "Senior",
                "input": [{"role": "user", "content": "CALL_TOOL get the weather"}],
                "stream": True,
                "store": False,
                "tools": [TOOL],
                "max_output_tokens": 100,
            },
        ) as resp:
            assert resp.status_code == 200, f"status {resp.status_code}: {resp.text}"
            events, saw_done = _parse_sse(resp)
    finally:
        client.close()

    names = [name for name, _ in events]
    assert "response.output_item.done" in names, f"缺 output_item.done: {names}"
    items = [
        d.get("item")
        for n, d in events
        if n == "response.output_item.done" and isinstance(d.get("item"), dict)
    ]
    function_calls = [it for it in items if it.get("type") == "function_call"]
    assert function_calls, (
        f"上游未回传 function_call——无法证明其收到 tools（透传不可证伪）: {items}"
    )
    assert any(it.get("name") == TOOL["name"] for it in function_calls), (
        f"上游回传的 function_call.name 不等于所发工具名 {TOOL['name']!r}（透传证据不成立）: {function_calls}"
    )
    assert saw_done, "SSE 流缺 data: [DONE]"
