"""Case ID: ST-DEPL-008

Endpoint: POST /v1/deployments
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

目标：验证 provider_id 不存在时 → 400 invalid_request。

断言：
- HTTP 400
- error 键集恰 5 键；code == "invalid_request"、type == "request_error"
- error.param == "provider_id"、retryable == False
- 零副作用：deployment 集合未变
"""
from __future__ import annotations

import pytest

ERROR_KEYS = {"message", "type", "code", "param", "retryable"}


@pytest.mark.api_b
def test_adm_depl_08_nonexistent_provider(admin_client_b):
    before = admin_client_b.get("/v1/deployments")
    assert before.status_code == 200
    before_ids = {d["id"] for d in before.json()["data"]}

    body = {
        "name": "Deployment Bad Provider",
        "provider_id": "nonexistent_provider",
        "backend_model": "test-model",
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
    }
    resp = admin_client_b.post("/v1/deployments", json=body)
    assert resp.status_code == 400, f"期望 400，实际 {resp.status_code}: {resp.text}"
    body_json = resp.json()
    assert set(body_json) == {"error"}, f"顶层键集不符: {set(body_json)}"
    err = body_json["error"]
    assert set(err) == ERROR_KEYS, f"error 键集不符（恰 5 键）: {set(err)}"
    assert err["code"] == "invalid_request"
    assert err["type"] == "request_error", f"type != request_error: {err}"
    assert err["param"] == "provider_id", f"期望 param=provider_id，实际 {err['param']!r}"
    assert err["retryable"] is False, f"retryable != False: {err}"

    after = admin_client_b.get("/v1/deployments")
    assert after.status_code == 200
    after_ids = {d["id"] for d in after.json()["data"]}
    assert after_ids == before_ids, f"被拒 POST 产生了副作用: {after_ids - before_ids}"
