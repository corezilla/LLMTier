"""Case ID: ADM-DEPL-02

Endpoint: POST /tier/admin/v1/deployments
Upstream Provider: 无（测试 CRUD 路由）
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 201
- body 含完整 deployment 对象（id, name, provider_id, backend_model, capabilities, enabled, version）
- ETag response header 存在
- capabilities 含全部 12 个字段
"""
from __future__ import annotations

import pytest

BASELINE_PROVIDER_ID = "prov_b"


@pytest.mark.api_b
def test_adm_depl_02_create_deployment(admin_client_b):
    body = {
        "name": "New Test Deployment",
        "provider_id": BASELINE_PROVIDER_ID,
        "backend_model": "test-model-01",
        "capabilities": {
            "responses": True,
            "embeddings": False,
            "tools": True,
            "structured_outputs": False,
            "input_modalities": ["text"],
            "output_modalities": ["text"],
            "context_window": 8192,
            "max_output_tokens": 4096,
            "embedding_space_id": None,
            "embedding_dimensions": None,
            "embedding_max_batch_inputs": None,
            "embedding_max_input_tokens": None,
        },
        "enabled": True,
    }
    resp = admin_client_b.post("/tier/admin/v1/deployments", json=body)
    assert resp.status_code == 201, f"期望 201，实际 {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["name"] == body["name"]
    assert data["provider_id"] == body["provider_id"]
    assert data["backend_model"] == body["backend_model"]
    assert data["enabled"] == body["enabled"]
    assert data["capabilities"] == body["capabilities"]
    assert "id" in data
    assert "version" in data
    assert "ETag" in resp.headers

    rid = data["id"]
    etag = resp.headers["ETag"]
    get_resp = admin_client_b.get(f"/tier/admin/v1/deployments/{rid}")
    assert get_resp.status_code == 200
    assert get_resp.headers.get("ETag") == etag
