"""Case ID: DP-RESP-08

Endpoint: POST /v1/responses (missing model)
Upstream Provider: 无
Model: 无
Auth: Bearer dev-data

断言：
- HTTP 400
- error.code == "invalid_request"
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_dp_resp_08_missing_model(api_client):
    resp = api_client.post(
        "/v1/responses",
        json={
            "input": [{"role": "user", "content": "hi"}],
            "stream": True,
            "store": False,
        },
    )
    assert resp.status_code == 400, f"返回 {resp.status_code}（期望 400）: {resp.text}"
    body = resp.json()
    err = body.get("error") or {}
    assert err.get("code") == "invalid_request", f"error.code != 'invalid_request': {err}"
