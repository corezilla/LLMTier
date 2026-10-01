"""Case ID: ST-SL-002

Endpoint: POST /v1/service-levels
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- POST body.id 不是 FIXED_TIER（如 "CustomTier"）
- HTTP 400
- error 键集恰 5 键；code == "invalid_request"、type == "request_error"
- error.param == "id"、retryable == False；message 含 "not a fixed Tier"
- 零副作用：GET /v1/service-levels 中无 CustomTier
"""
from __future__ import annotations

from tests.system.constants import FIXED_TIERS

import pytest

ERROR_KEYS = {"message", "type", "code", "param", "retryable"}


@pytest.mark.api_b
def test_adm_sl_02_create_non_fixed_tier(admin_client_b):
    resp = admin_client_b.post("/v1/service-levels", json={
        "id": "CustomTier",
        "deployment_ids": ["depl_b"],
        "enabled": True,
    })
    assert resp.status_code == 400, f"期望 400，实际 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert set(body) == {"error"}, f"顶层键集不符: {set(body)}"
    err = body["error"]
    assert set(err) == ERROR_KEYS, f"error 键集不符（恰 5 键）: {set(err)}"
    assert err["code"] == "invalid_request"
    assert err["type"] == "request_error", f"type != request_error: {err}"
    assert err["param"] == "id", f"param != id: {err}"
    assert err["retryable"] is False, f"retryable != False: {err}"
    assert "not a fixed Tier" in err["message"], f"message 不符: {err}"

    after = admin_client_b.get("/v1/service-levels")
    assert after.status_code == 200
    ids = {s["id"] for s in after.json()["data"]}
    assert "CustomTier" not in ids, "被拒 POST 创建了 CustomTier（副作用）"
    assert set(FIXED_TIERS) <= ids, f"7 个固定 Tier 应仍在，实际: {ids}"
