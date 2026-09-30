"""Case ID: ADM-SL-02b

Endpoint: POST /v1/service-levels
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

前置条件：FIXED_TIER "Senior" 已存在（baseline 预创建）

断言：
- POST body.id == "Senior"（已存在）
- HTTP 409
- error 键集恰 5 键；code == "resource_conflict"、type == "request_error"、retryable == False
- 零副作用：Senior 仍存在且 version 不变
"""
from __future__ import annotations

import pytest

ERROR_KEYS = {"message", "type", "code", "param", "retryable"}


@pytest.mark.api_b
def test_adm_sl_02b_create_duplicate_fixed_tier(admin_client_b):
    before = admin_client_b.get("/v1/service-levels/Senior")
    assert before.status_code == 200
    version_before = before.json()["version"]

    resp = admin_client_b.post("/v1/service-levels", json={
        "id": "Senior",
        "deployment_ids": ["depl_b"],
        "enabled": True,
    })
    assert resp.status_code == 409, f"期望 409，实际 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert set(body) == {"error"}, f"顶层键集不符: {set(body)}"
    err = body["error"]
    assert set(err) == ERROR_KEYS, f"error 键集不符（恰 5 键）: {set(err)}"
    assert err["code"] == "resource_conflict"
    assert err["type"] == "request_error", f"type != request_error: {err}"
    assert err["retryable"] is False, f"retryable != False: {err}"

    after = admin_client_b.get("/v1/service-levels/Senior")
    assert after.status_code == 200, "Senior 应仍然存在"
    assert after.json()["version"] == version_before, (
        f"被拒 POST 改动了 Senior.version: {version_before} -> {after.json()['version']}")
