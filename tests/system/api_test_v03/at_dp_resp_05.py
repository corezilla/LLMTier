"""Case ID: DP-RESP-05

Endpoint: POST /v1/responses (unknown model)
Upstream Provider: 无
Model: NonExistentModel
Auth: Bearer dev-data

断言：
- HTTP 404
- error.code == "not_found"

注：model 不在 7 个 FIXED_TIERS 时，service-level 查找先于 routing 命中，
抛 not_found（不是 model_not_found——model_not_found 是另一条路径：service-level
存在但无 enabled deployment）。
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
    assert err.get("code") == "not_found", f"error.code != 'not_found': {err}"
