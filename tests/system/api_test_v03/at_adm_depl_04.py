"""Case ID: ADM-DEPL-04

Endpoint: PATCH /tier/admin/v1/deployments/{id}
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

依赖：先创建一个 deployment（由 ADM-DEPL-02 创建，或本 case 自创）

断言：
- HTTP 200
- body 含更新后的 deployment
- ETag response header 存在且值比请求前新
- 字段 name / enabled 确实被更新
"""
from __future__ import annotations

import pytest

BASELINE_PROVIDER_ID = "prov_b"


@pytest.mark.api_b
def test_adm_depl_04_update_deployment(admin_client_b):
    create_resp = admin_client_b.post("/tier/admin/v1/deployments", json={
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

    patch_resp = admin_client_b.patch(
        f"/tier/admin/v1/deployments/{rid}",
        json={"name": "Updated Deployment Name", "enabled": False},
        headers={"If-Match": original_etag},
    )
    assert patch_resp.status_code == 200, f"期望 200，实际 {patch_resp.status_code}: {patch_resp.text}"
    updated = patch_resp.json()
    assert updated["name"] == "Updated Deployment Name"
    assert updated["enabled"] is False
    assert updated["version"] > depl["version"]
    assert "ETag" in patch_resp.headers
