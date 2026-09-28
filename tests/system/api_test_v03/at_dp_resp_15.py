"""Case ID: DP-RESP-15

Endpoint: POST /v1/responses
Upstream Provider: m5air OMLX (Qwen3.6)
Model: Worker
Auth: Bearer dev-data

目标：temperature 是合法可选字段（被受理）；top_p 不在 ResponsesRequest/
ALLOWED_FIELDS 中，出现即触发未知字段拒绝。

断言：
- (a) 仅 temperature：HTTP 200，返回 SSE（含 response.completed）
- (b) temperature + top_p：HTTP 400，error.code == "invalid_request"
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_dp_resp_15_temperature_top_p(api_client):
    accepted_body = {
        "model": "Worker",
        "input": [{"role": "user", "content": "say hello"}],
        "stream": True,
        "store": False,
        "temperature": 0.7,
    }
    with api_client.stream("POST", "/v1/responses", json=accepted_body) as resp:
        assert resp.status_code == 200, f"temperature 单独应受理，实际 {resp.status_code}: {resp.text}"
        ct = resp.headers.get("content-type", "")
        assert "text/event-stream" in ct, f"content-type={ct!r}, expect text/event-stream"
        from tests.system.api_test_v03.conftest import parse_sse_raw

        names = [e[0] for e in parse_sse_raw(resp)]
    assert "response.completed" in names, f"缺 response.completed: {names}"

    resp = api_client.post(
        "/v1/responses",
        json={**accepted_body, "top_p": 0.9},
    )
    assert resp.status_code == 400, f"期望 400，实际 {resp.status_code}: {resp.text}"
    err = resp.json().get("error") or {}
    assert err.get("code") == "invalid_request", f"error.code != 'invalid_request': {err}"
