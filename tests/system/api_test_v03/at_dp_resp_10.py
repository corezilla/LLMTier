"""Case ID: DP-RESP-10

Endpoint: POST /v1/responses
Upstream Provider: m5air OMLX (Qwen3.6)
Model: Worker
Auth: Bearer dev-data

目标：验证 max_output_tokens truncation 行为。

前置（能力门）：GET /v1/models 确认所选 tier 的 capabilities.max_output_tokens >= 10，
否则 BLOCKED（能力上界不足，不能构造截断）。

断言：
- HTTP 200，Content-Type: text/event-stream
- 恰一个 terminal，且为 response.incomplete（不是 response.completed）
- response.incomplete.response.status == "incomplete"
- response.incomplete_details.reason == "max_output_tokens"
- 各帧 sequence_number 严格递增
- 流末尾出现 data: [DONE]

注：context_window 硬上限（262k tokens）在 Qwen3.6 上实测未触发 API 层错误；
真正可测的边界是 max_output_tokens truncation。
"""
from __future__ import annotations

from tests.system.api_test_v03.conftest import post_stream_collect

import pytest


@pytest.mark.api_a
def test_dp_resp_10_max_output_tokens_truncated(api_client):
    # 能力门：确认 max_output_tokens 上界足以承载 10。
    models = api_client.get("/v1/models")
    assert models.status_code == 200, f"/v1/models 返回 {models.status_code}: {models.text}"
    worker = next((m for m in models.json()["data"] if m["id"] == "Worker"), None)
    assert worker is not None, "Worker 不在 /v1/models 清单中"
    limit = (worker.get("capabilities") or {}).get("max_output_tokens")
    if not (isinstance(limit, int) and limit >= 10):
        pytest.skip(f"BLOCKED (DP-RESP-10): Worker.capabilities.max_output_tokens={limit} < 10")

    events, saw_done = post_stream_collect(
        api_client,
        {
            "model": "Worker",
            "input": [{"role": "user", "content": "Count from 1 to 1000. Output only numbers separated by commas."}],
            "stream": True,
            "store": False,
            "max_output_tokens": 10,
        },
    )

    names = [name for name, _ in events]
    assert "response.created" in names, f"缺 response.created: {names}"

    terminal_names = {"response.completed", "response.incomplete", "response.failed"}
    terminals = [n for n in names if n in terminal_names]
    assert len(terminals) == 1, (
        f"应恰有 1 个 terminal（截断不得与 completed 并存），实际 {terminals}: {names}"
    )
    assert terminals[0] == "response.incomplete", f"terminal 应为 response.incomplete: {terminals}"

    incomplete_event = next(d for n, d in events if n == "response.incomplete")
    response = incomplete_event.get("response") or {}
    assert response.get("status") == "incomplete", f"status != 'incomplete': {response.get('status')}"
    details = response.get("incomplete_details") or {}
    assert details.get("reason") == "max_output_tokens", \
        f"期望 incomplete_details.reason=max_output_tokens，实际 {details}"

    seqs = [d["sequence_number"] for _, d in events if isinstance(d, dict) and "sequence_number" in d]
    for i in range(1, len(seqs)):
        assert seqs[i] > seqs[i - 1], f"sequence_number 非严格递增: {seqs}"

    assert saw_done, "SSE 流缺 data: [DONE]（截断仍应正常收尾）"
