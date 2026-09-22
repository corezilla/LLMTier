"""Case ID: ADM-SL-07

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
"""
from __future__ import annotations

import pytest


@pytest.mark.api_b
def test_adm_sl_07_embedding_space_conflict(admin_client_b):
    get_resp = admin_client_b.get("/v1/service-levels/Embedding-v1")
    assert get_resp.status_code == 200
    etag = get_resp.headers.get("ETag")

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

    patch_resp = admin_client_b.patch(
        "/v1/service-levels/Embedding-v1",
        json={"deployment_ids": [new_depl_id]},
        headers={"If-Match": etag},
    )
    assert patch_resp.status_code == 409, f"期望 409，实际 {patch_resp.status_code}: {patch_resp.text}"
    err = patch_resp.json().get("error") or {}
    assert err.get("code") == "embedding_space_conflict"
