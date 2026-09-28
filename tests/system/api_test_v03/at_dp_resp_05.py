"""Case ID: DP-RESP-05

Endpoint: POST /v1/responses (unknown model)
Upstream Provider: 无
Model: NonExistentModel
Auth: Bearer dev-data

断言：
- HTTP 404
- error.code == "model_not_found"

注：model 不在 7 个 FIXED_TIERS 时，registry.get_service_level 先抛 404 not_found；
ResponsesService.create 捕获该 404 并 remap 为 404 model_not_found
（src/inference/responses.py:79-82）。
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_dp_resp_05_unknown_model(api_client):
    resp = api_client.post(
        "/v1/responses",
        json={
            "model": "NonExistentModel",
            "input": [{"role": "user", "content": "hi"}],
            "stream": True,
            "store": False,
        },
    )
    assert resp.status_code == 404, f"返回 {resp.status_code}（期望 404）: {resp.text}"
    body = resp.json()
    err = body.get("error") or {}
    assert err.get("code") == "model_not_found", f"error.code != 'model_not_found': {err}"
