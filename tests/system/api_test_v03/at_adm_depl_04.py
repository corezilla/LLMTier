"""Case ID: ST-DEPL-004

Endpoint: PATCH /v1/deployments/{id}
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

依赖：先创建一个 deployment（本 case 自创，finally 内删除）

断言：
- HTTP 200，name / enabled 确实被更新
- version == original + 1（精确）
- 新 ETag == f'"{rid}.v{version}"'
- provider_id / backend_model / capabilities 未提交字段保持原值
- GET 回读：新值持久化且 ETag 与新响应头一致
- teardown：DELETE（最新 ETag）→ 204，随后 GET → 404
"""
from __future__ import annotations

import pytest

BASELINE_PROVIDER_ID = "prov_b"


@pytest.mark.api_b
def test_adm_depl_04_update_deployment(admin_client_b):
    create_resp = admin_client_b.post("/v1/deployments", json={
        "name": "Deployment To Update",
        "provider_id": BASELINE_PROVIDER_ID,
        "backend_model": "test-model-update",
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
    assert create_resp.status_code == 201
    depl = create_resp.json()
    rid = depl["id"]
    original_etag = create_resp.headers["ETag"]
    original_version = depl["version"]

    try:
        patch_resp = admin_client_b.patch(
            f"/v1/deployments/{rid}",
            json={"name": "Updated Deployment Name", "enabled": False},
            headers={"If-Match": original_etag},
        )
        assert patch_resp.status_code == 200, f"期望 200，实际 {patch_resp.status_code}: {patch_resp.text}"
        updated = patch_resp.json()
        assert updated["name"] == "Updated Deployment Name"
        assert updated["enabled"] is False
        assert updated["version"] == original_version + 1, (
            f"version 应精确 +1：{original_version} -> {updated['version']}")
        new_etag = patch_resp.headers.get("ETag")
        assert new_etag == f'"{rid}.v{updated["version"]}"', (
            f"新 ETag 不符: {new_etag!r} vs \"{rid}.v{updated['version']}\"")
        assert updated["provider_id"] == depl["provider_id"], "provider_id 不应被更改"
        assert updated["backend_model"] == depl["backend_model"], "backend_model 不应被更改"
        assert updated["capabilities"] == depl["capabilities"], "capabilities 不应被更改"

        read_resp = admin_client_b.get(f"/v1/deployments/{rid}")
        assert read_resp.status_code == 200
        readback = read_resp.json()
        assert readback["name"] == "Updated Deployment Name"
        assert readback["enabled"] is False
        assert readback["version"] == updated["version"]
        assert read_resp.headers.get("ETag") == new_etag, "回读 ETag 与 PATCH 响应头不一致"
    finally:
        current = admin_client_b.get(f"/v1/deployments/{rid}")
        if current.status_code == 200:
            del_resp = admin_client_b.delete(
                f"/v1/deployments/{rid}",
                headers={"If-Match": current.headers["ETag"]},
            )
            assert del_resp.status_code == 204, f"teardown DELETE 失败: {del_resp.status_code}: {del_resp.text}"
            assert admin_client_b.get(f"/v1/deployments/{rid}").status_code == 404
