"""Case ID: ST-resp-026

Endpoint: PATCH /v1/deployments/depl_b/diagnostics（注入写）;
          POST /v1/responses（stream=true，被测流）
Upstream Provider: prov_b（LAN fake provider，test-model）
Model: Senior（指向 depl_b，probe healthy）
Auth: 注入写 Bearer dev-admin；响应 Bearer dev-data

TS-002 依赖：
  Endpoint: 临时 LLMTier 实例（llmtier_b）
  上游: LAN fake provider（TS-003；conftest 在机器 LAN IP 起 v03_fake_provider）
  模型: Senior
  注入: stream_terminate / stream_terminate_after_events=2

目标：注入 stream_terminate 后，POST /v1/responses（stream=true）的 SSE 流在
达到 stream_terminate_after_events 个事件后提前结束（不再有 terminal 事件与
[DONE]），客户端可观察到截断。实现 src/libdiag/stream.py::stream_wrapper。
"""
from __future__ import annotations

import httpx
import pytest

DIAG_PATH = "/v1/deployments/depl_b/diagnostics"
RESPONSES_BODY = {
    "model": "Senior",
    "input": [{"role": "user", "content": "Hello"}],
    "stream": True,
    "store": False,
}
TERMINATE_AFTER = 2


def _read_stream_bytes(inst, body: dict) -> tuple[int, dict, bytes]:
    with httpx.Client(
        base_url=inst.base_url,
        headers={"Authorization": "Bearer dev-data"},
        timeout=httpx.Timeout(30.0, connect=5.0),
    ) as client:
        with client.stream("POST", "/v1/responses", json=body) as resp:
            status = resp.status_code
            headers = dict(resp.headers)
            chunks = b"".join(resp.iter_bytes())
    return status, headers, chunks


@pytest.mark.api_b
def test_dp_resp_26_stream_terminate(admin_client_b, api_client_b, llmtier_b):
    injection = {
        "items": [
            {
                "type": "stream_terminate",
                "config": {"stream_terminate_after_events": TERMINATE_AFTER},
                "enabled": True,
            }
        ]
    }
    try:
        set_resp = admin_client_b.patch(DIAG_PATH, json=injection)
        assert set_resp.status_code == 200, (
            f"写入 stream_terminate 失败: {set_resp.status_code}: {set_resp.text}"
        )
        configured = set_resp.json()
        assert any(
            item.get("type") == "stream_terminate" and item.get("enabled")
            for item in configured
        ), f"stream_terminate 未生效: {configured}"

        status, headers, raw = _read_stream_bytes(llmtier_b, RESPONSES_BODY)
        assert status == 200, f"流响应期望 200，实际 {status}: {raw[:500]!r}"
        assert headers.get("content-type", "").startswith("text/event-stream"), (
            f"Content-Type 不符: {headers.get('content-type')}"
        )

        # The stream is truncated: no terminal event, no [DONE].
        assert b"response.completed" not in raw, f"截断流不应含 terminal: {raw!r}"
        assert b"response.failed" not in raw, f"截断流不应含 terminal: {raw!r}"
        assert b"[DONE]" not in raw, f"截断流不应含 [DONE]: {raw!r}"

        # Exactly TERMINATE_AFTER events emitted (the stream_wrapper counts chunks).
        events = [line for line in raw.split(b"\n") if line.startswith(b"event:")]
        assert len(events) == TERMINATE_AFTER, (
            f"截断点应为 {TERMINATE_AFTER} 个事件，实际 {len(events)}: {raw!r}"
        )
    finally:
        clear = admin_client_b.patch(DIAG_PATH, json={"items": []})
        assert clear.status_code == 200, f"清空注入失败: {clear.status_code}: {clear.text}"
        remaining = admin_client_b.get(DIAG_PATH)
        assert remaining.status_code == 200
        assert all(not item.get("enabled") for item in remaining.json()), (
            f"注入未清空: {remaining.json()}"
        )
