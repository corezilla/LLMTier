"""Case ID: DP-RESP-07

Endpoint: POST /v1/responses (store=true)
Upstream Provider: 无
Model: Worker
Auth: Bearer dev-data

断言：
- HTTP 400
- error.code == "unsupported_request"
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_dp_resp_07_store_true_rejected(api_client):
    resp = api_client.post(
        "/v1/responses",
        json={
            "model": "Worker",
            "input": [{"role": "user", "content": "hi"}],
            "stream": True,
            "store": True,
        },
    )
    assert resp.status_code == 400, f"返回 {resp.status_code}（期望 400）: {resp.text}"
    body = resp.json()
    err = body.get("error") or {}
    assert err.get("code") == "unsupported_request", (
        f"error.code != 'unsupported_request': {err}"
    )
