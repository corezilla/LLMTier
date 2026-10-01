"""Case ID: ST-resp-027

Endpoint: PATCH /v1/deployments/depl_b/diagnostics（注入写）;
          POST /v1/responses（stream=true，被测流）
Upstream Provider: prov_b（LAN fake provider，test-model）
Model: Senior（指向 depl_b，probe healthy）
Auth: 注入写 Bearer dev-admin；响应 Bearer dev-data

TS-002 依赖：
  Endpoint: 临时 LLMTier 实例（llmtier_b）
  上游: LAN fake provider（TS-003；conftest 在机器 LAN IP 起 v03_fake_provider）
  模型: Senior
  注入: malformed_event / malformed_after_events=1，malformed_event_type 子测

目标：注入 malformed_event 后，POST /v1/responses（stream=true）的 SSE 流在达到
malformed_after_events 个事件后追加一个畸形帧（`event: response.malformed` +
非法 JSON `data:`）随后结束，客户端解析该帧会失败。实现 src/libdiag/stream.py
（`_MALFORMED_FRAME`）。

注意（doc discrepancy，见 Run 报告）：实现 `stream_wrapper` 对
`malformed_event_type` 不区分，两种子测追加同一 `_MALFORMED_FRAME`
（事件名 `response.malformed` 不在契约白名单，data 亦非法 JSON）。因此
`invalid_json` 与 `unknown_event_type` 两子测断言同一帧形态（该帧同时满足
两个子测语义）；不伪造差异。
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
MALFORMED_AFTER = 1
MALFORMED_EVENT_TYPE = "response.malformed"


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


def _assert_malformed_frame(raw: bytes) -> None:
    marker = f"event: {MALFORMED_EVENT_TYPE}\n".encode()
    idx = raw.find(marker)
    assert idx != -1, f"未发现畸形帧 {MALFORMED_EVENT_TYPE}: {raw!r}"
    # data line immediately follows the malformed event name and is invalid JSON.
    tail = raw[idx + len(marker):]
    data_line = tail.split(b"\n", 1)[0]
    assert data_line.startswith(b"data:"), f"畸形帧缺少 data 行: {tail[:200]!r}"
    payload = data_line[len(b"data:"):].strip()
    import json as _json

    with pytest.raises(ValueError):
        _json.loads(payload)
    # Frame terminates the stream: no terminal event / [DONE] after it.
    assert b"response.completed" not in raw, f"畸形帧流不应含 terminal: {raw!r}"
    assert b"[DONE]" not in raw, f"畸形帧流不应含 [DONE]: {raw!r}"


@pytest.mark.api_b
@pytest.mark.parametrize("malformed_event_type", ["invalid_json", "unknown_event_type"])
def test_dp_resp_27_malformed_event(admin_client_b, api_client_b, llmtier_b, malformed_event_type):
    injection = {
        "items": [
            {
                "type": "malformed_event",
                "config": {
                    "malformed_after_events": MALFORMED_AFTER,
                    "malformed_event_type": malformed_event_type,
                },
                "enabled": True,
            }
        ]
    }
    try:
        set_resp = admin_client_b.patch(DIAG_PATH, json=injection)
        assert set_resp.status_code == 200, (
            f"写入 malformed_event 失败: {set_resp.status_code}: {set_resp.text}"
        )
        configured = set_resp.json()
        assert any(
            item.get("type") == "malformed_event" and item.get("enabled")
            for item in configured
        ), f"malformed_event 未生效: {configured}"

        status, headers, raw = _read_stream_bytes(llmtier_b, RESPONSES_BODY)
        assert status == 200, f"流响应期望 200，实际 {status}: {raw[:500]!r}"
        assert headers.get("content-type", "").startswith("text/event-stream"), (
            f"Content-Type 不符: {headers.get('content-type')}"
        )
        _assert_malformed_frame(raw)
    finally:
        clear = admin_client_b.patch(DIAG_PATH, json={"items": []})
        assert clear.status_code == 200, f"清空注入失败: {clear.status_code}: {clear.text}"
        remaining = admin_client_b.get(DIAG_PATH)
        assert remaining.status_code == 200
        assert all(not item.get("enabled") for item in remaining.json()), (
            f"注入未清空: {remaining.json()}"
        )
