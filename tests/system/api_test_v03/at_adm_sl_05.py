"""Case ID: ADM-SL-05

Endpoint: DELETE /v1/service-levels/{id}
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

目标：固定 Tier 不可删除（409 fixed_service_level）。

为使 409 具备判别力，加入可达的**正对照**：DELETE 一个可删除资源（本 case 自建 deployment）
成功返回 204——证明 409 并非"DELETE 一律失败"的默认行为。系统当前不存在任何非固定 Tier
（`create_service_level` 仅接受 FIXED_TIERS，`delete_service_level` 也无条件 409），故无法
以"非固定 Tier 删除成功"作正对照；以 deployment 删除成功作为 DELETE 动词的正对照。

断言：
- 正对照：POST 一个 deployment → DELETE（If-Match）→ 204，随后 GET → 404
- DELETE Engineer → 409；error 恰 5 键；code == "fixed_service_level"、type == "request_error"
- message 含 "cannot be deleted"、retryable == False
- 零副作用：Engineer.version 不变；7 tier 齐全
"""
from __future__ import annotations

from tests.system.api_test_v03.constants import FIXED_TIERS

import pytest

ERROR_KEYS = {"message", "type", "code", "param", "retryable"}


@pytest.mark.api_b
def test_adm_sl_05_delete_fixed_tier(admin_client_b):
    # Positive control: the DELETE handler can return 204 for a deletable resource.
    control = admin_client_b.post("/v1/deployments", json={
        "name": "Deployment To Delete (SL-05 control)",
        "provider_id": "prov_b",
        "backend_model": "test-model-sl05",
        "capabilities": {
            "responses": True,
            "embeddings": False,
            "tools": False,
            "structured_outputs": False,
            "input_modalities": ["text"],
            "output_modalities": ["text"],
            "context_window": 4096,
            "max_output_tokens": 2048,
            "embedding_space_id": None,
            "embedding_dimensions": None,
            "embedding_max_batch_inputs": None,
            "embedding_max_input_tokens": None,
        },
        "enabled": True,
    })
    assert control.status_code == 201
    control_id = control.json()["id"]
    control_etag = control.headers["ETag"]
    control_del = admin_client_b.delete(f"/v1/deployments/{control_id}", headers={"If-Match": control_etag})
    assert control_del.status_code == 204, (
        f"正对照 DELETE deployment 期望 204，实际 {control_del.status_code}: {control_del.text}")
    assert admin_client_b.get(f"/v1/deployments/{control_id}").status_code == 404

    get_resp = admin_client_b.get("/v1/service-levels/Engineer")
    assert get_resp.status_code == 200
    etag = get_resp.headers.get("ETag")
    version_before = get_resp.json()["version"]

    del_resp = admin_client_b.delete(
        "/v1/service-levels/Engineer",
        headers={"If-Match": etag},
    )
    assert del_resp.status_code == 409, f"期望 409，实际 {del_resp.status_code}: {del_resp.text}"
    body = del_resp.json()
    assert set(body) == {"error"}, f"顶层键集不符: {set(body)}"
    err = body["error"]
    assert set(err) == ERROR_KEYS, f"error 键集不符（恰 5 键）: {set(err)}"
    assert err["code"] == "fixed_service_level"
    assert err["type"] == "request_error", f"type != request_error: {err}"
    assert err["retryable"] is False, f"retryable != False: {err}"
    assert "cannot be deleted" in err["message"], f"message 不符: {err}"

    after = admin_client_b.get("/v1/service-levels/Engineer")
    assert after.status_code == 200, "Engineer 不应被删除"
    assert after.json()["version"] == version_before, "被拒 DELETE 改动了 Engineer.version"
    listing = admin_client_b.get("/v1/service-levels")
    assert listing.status_code == 200
    ids = {s["id"] for s in listing.json()["data"]}
    assert set(FIXED_TIERS) <= ids, f"7 tier 应齐全，实际: {ids}"
