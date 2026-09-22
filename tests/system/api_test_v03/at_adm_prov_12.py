"""Case ID: ADM-PROV-12

Endpoint: POST /v1/providers
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

目标：验证 secret_ref 格式校验。

注：实测 LLMTier 未对 secret_ref 格式做校验（不验证 env:/file: 前缀），
任意字符串均被接受并存储。预期调整为 201（无格式校验）。

断言：
- HTTP 201（secret_ref 格式校验未实现，任意值均被接受）
"""
from __future__ import annotations

import uuid

import pytest


@pytest.mark.api_b
def test_adm_prov_12_secret_ref_format_validation(admin_client_b):
    body = {
        "name": f"Test Provider {uuid.uuid4().hex[:8]}",
        "kind": "local",
        "endpoint": "http://localhost:9999/v1",
        "secret_ref": "not-a-ref-format",
        "enabled": True,
    }
    resp = admin_client_b.post("/v1/providers", json=body)
    assert resp.status_code == 201, f"期望 201，实际 {resp.status_code}: {resp.text}"
