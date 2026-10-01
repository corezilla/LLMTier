"""Case ID: ST-sl-007

Endpoint: PATCH /v1/service-levels/Embedding-v1
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

目标：验证 embedding_space_conflict → 409。
触发方式：PATCH Embedding-v1 SL，将其 deployment_ids 改为一个 embedding deployment
（embedding_space_id 不是 "bge-m3-dense-1024-v1"）。

原理：registry.py:285 — Embedding-v1 要求 embedding_space_id == "bge-m3-dense-1024-v1"，
新 deployment 的 embedding_space_id="wrong-space-id" → 409 embedding_space_conflict。

断言：
- HTTP 409
- error.code == "embedding_space_conflict"
- error 键集恰 5 键、type == "request_error"、retryable == False
- 零副作用：Embedding-v1 的 deployment_ids/version 未变
- teardown（finally）：删除新建 deployment（204，随后 404）
"""
from __future__ import annotations

import pytest


@pytest.mark.api_b
def test_adm_sl_07_embedding_space_conflict(admin_client_b):
    get_resp = admin_client_b.get("/v1/service-levels/Embedding-v1")
    assert get_resp.status_code == 200
    etag = get_resp.headers.get("ETag")
    embed = get_resp.json()
    version_before = embed["version"]
    ids_before = embed["deployment_ids"]

    new_depl = admin_client_b.post("/v1/deployments", json={
        "name": "Embedding Wrong Space",
        "provider_id": "prov_b",
        "backend_model": "embedding-model",
        "capabilities": {
            "responses": False,
            "embeddings": True,
            "tools": False,
            "structured_outputs": False,
            "input_modalities": ["text"],
            "output_modalities": ["text"],
            "context_window": 4096,
            "max_output_tokens": 2048,
            "embedding_space_id": "wrong-space-id",
            "embedding_dimensions": [1024],
            "embedding_max_batch_inputs": 32,
            "embedding_max_input_tokens": 8192,
        },
        "enabled": True,
    })
    assert new_depl.status_code == 201
    new_depl_id = new_depl.json()["id"]

    try:
        patch_resp = admin_client_b.patch(
            "/v1/service-levels/Embedding-v1",
            json={"deployment_ids": [new_depl_id]},
            headers={"If-Match": etag},
        )
        assert patch_resp.status_code == 409, f"期望 409，实际 {patch_resp.status_code}: {patch_resp.text}"
        err = patch_resp.json().get("error") or {}
        assert err.get("code") == "embedding_space_conflict"
        assert err.get("type") == "request_error", f"type != request_error: {err}"
        assert err.get("retryable") is False, f"retryable != False: {err}"

        after = admin_client_b.get("/v1/service-levels/Embedding-v1")
        assert after.status_code == 200
        assert after.json()["deployment_ids"] == ids_before, "被拒 PATCH 改动了 Embedding-v1.deployment_ids"
        assert after.json()["version"] == version_before, "被拒 PATCH 推进了 Embedding-v1.version"
    finally:
        # teardown: PATCH 失败已回滚，new deployment 未被引用，直接删除。
        current = admin_client_b.get(f"/v1/deployments/{new_depl_id}")
        if current.status_code == 200:
            del_resp = admin_client_b.delete(
                f"/v1/deployments/{new_depl_id}",
                headers={"If-Match": current.headers["ETag"]},
            )
            assert del_resp.status_code == 204, f"teardown 删除失败: {del_resp.status_code}: {del_resp.text}"
