"""Case ID: DP-RESP-09

Endpoint: POST /v1/responses (previous_response_id)
Upstream Provider: 无
Model: Worker
Auth: Bearer dev-data

断言：
- HTTP 400
- error.code == "unsupported_field"
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_dp_resp_09_previous_response_id_rejected(api_client):
    resp = api_client.post(
        "/v1/responses",
        json={
            "model": "Worker",
            "input": [{"role": "user", "content": "hi"}],
            "stream": True,
            "store": False,
            "previous_response_id": "resp_xxx",
        },
    )
    assert resp.status_code == 400, f"返回 {resp.status_code}（期望 400）: {resp.text}"
    body = resp.json()
    err = body.get("error") or {}
    assert err.get("code") == "unsupported_field", f"error.code != 'unsupported_field': {err}"
