"""Case ID: ADM-PROV-11

Endpoint: POST /v1/providers
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

目标：验证 kind 字段枚举校验；无效值 → 400。

断言：
- HTTP 400
- error.code == "invalid_request"
"""
from __future__ import annotations

import uuid

import pytest


@pytest.mark.api_b
def test_adm_prov_11_kind_enum_validation(admin_client_b):
    body = {
        "name": f"Test Provider {uuid.uuid4().hex[:8]}",
        "kind": "invalid_kind",
        "endpoint": "http://localhost:9999/v1",
        "secret_ref": None,
        "enabled": True,
    }
    resp = admin_client_b.post("/v1/providers", json=body)
    assert resp.status_code == 400, f"期望 400，实际 {resp.status_code}: {resp.text}"
    err = resp.json().get("error") or {}
    assert err.get("code") == "invalid_request"
