"""Case ID: ADM-DEPL-09

Endpoint: PATCH /v1/deployments/{id}
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

目标：验证 deployment 的 provider_id 不可变更——PATCH 一个**已存在**但不同的 provider_id
必须触发真正的 immutability 拒绝（400 invalid_request, param="provider_id"），且零副作用。

说明：若改为不存在的 provider_id，会命中 `Unknown provider` 这一独立的 400 分支，
无法证明 immutability；故本 case 先在基线实例中创建第二个 provider，再将其 id 作为 PATCH 值。

断言：
- 前置：创建第二个 provider prov_b2（finally 删除）
- HTTP 400
- error 键集恰 5 键；code == "invalid_request"、type == "request_error"
- error.param == "provider_id"、retryable == False
- 零副作用：depl_b 的 provider_id 仍为 prov_b、version/ETag 不变
"""
from __future__ import annotations

import pytest

BASELINE_PROVIDER_ID = "prov_b"

ERROR_KEYS = {"message", "type", "code", "param", "retryable"}


@pytest.mark.api_b
def test_adm_depl_09_provider_id_immutable(admin_client_b):
    # A second, EXISTING provider: the rejection must come from the immutability
    # guard, not from the independent unknown-provider 400.
    other_provider = admin_client_b.post("/v1/providers", json={
        "name": "Second Provider B",
        "kind": "local",
        "endpoint": "http://192.168.1.254:9/v1",
        "secret_ref": None,
        "enabled": True,
    })
    assert other_provider.status_code == 201, f"创建第二个 provider 失败: {other_provider.text}"
    other_provider_id = other_provider.json()["id"]
    assert other_provider_id != BASELINE_PROVIDER_ID

    try:
        depl_resp = admin_client_b.get("/v1/deployments/depl_b")
        assert depl_resp.status_code == 200
        before = depl_resp.json()
        etag = depl_resp.headers.get("ETag")
        assert before["provider_id"] == BASELINE_PROVIDER_ID

        patch_resp = admin_client_b.patch(
            "/v1/deployments/depl_b",
            json={"provider_id": other_provider_id},
            headers={"If-Match": etag},
        )
        assert patch_resp.status_code == 400, (
            f"期望 immutability 400，实际 {patch_resp.status_code}: {patch_resp.text}")
        body = patch_resp.json()
        assert set(body) == {"error"}, f"顶层键集不符: {set(body)}"
        err = body["error"]
        assert set(err) == ERROR_KEYS, f"error 键集不符（恰 5 键）: {set(err)}"
        assert err["code"] == "invalid_request"
        assert err["type"] == "request_error", f"type != request_error: {err}"
        assert err["param"] == "provider_id", f"期望 param=provider_id，实际 {err['param']!r}"
        assert err["retryable"] is False, f"retryable != False: {err}"

        after_resp = admin_client_b.get("/v1/deployments/depl_b")
        assert after_resp.status_code == 200
        after = after_resp.json()
        assert after["provider_id"] == before["provider_id"], "被拒 PATCH 改动了 provider_id"
        assert after["version"] == before["version"], (
            f"被拒 PATCH 推进了 version: {before['version']} -> {after['version']}")
        assert after_resp.headers.get("ETag") == etag, "被拒 PATCH 改动了 ETag"
    finally:
        current = admin_client_b.get(f"/v1/providers/{other_provider_id}")
        if current.status_code == 200:
            del_resp = admin_client_b.delete(
                f"/v1/providers/{other_provider_id}",
                headers={"If-Match": current.headers["ETag"]},
            )
            assert del_resp.status_code == 204, f"teardown 删除 provider 失败: {del_resp.text}"
