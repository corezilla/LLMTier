"""Case ID: ADM-DEPL-06

Endpoint: POST /tier/admin/v1/deployments
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

目标：验证 capabilities 缺字段时 → 400 invalid_request。

断言：
- HTTP 400
- error.code == "invalid_request"
"""
from __future__ import annotations

import pytest

BASELINE_PROVIDER_ID = "prov_b"


@pytest.mark.api_b
def test_adm_depl_06_capabilities_missing_field(admin_client_b):
    body = {
        "name": "Bad Deployment",
        "provider_id": BASELINE_PROVIDER_ID,
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
            # 故意缺 embedding_space_id 等字段
        },
        "enabled": True,
    }
    resp = admin_client_b.post("/tier/admin/v1/deployments", json=body)
    assert resp.status_code == 400, f"期望 400，实际 {resp.status_code}: {resp.text}"
    err = resp.json().get("error") or {}
    assert err.get("code") == "invalid_request"
