"""Case ID: ST-PROV-012

Endpoint: POST /v1/providers
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

目标：验证 secret_ref 格式校验（T-CFG-SECRET）。

secret_ref 仅接受 `env:` / `file:` 前缀（registry._validate_secret_ref）；
非法格式 → 400 invalid_request。

断言：
- HTTP 400
- error.code == "invalid_request"
- error.param == "secret_ref"
"""
from __future__ import annotations

import uuid

import pytest

from tests.system.api_test_v03.constants import LAN_PROVIDER_ENDPOINT


@pytest.mark.api_b
def test_adm_prov_12_secret_ref_format_validation(admin_client_b):
    body = {
        "name": f"Test Provider {uuid.uuid4().hex[:8]}",
        "kind": "local",
        "endpoint": LAN_PROVIDER_ENDPOINT,
        "secret_ref": "not-a-ref-format",
        "enabled": True,
    }
    resp = admin_client_b.post("/v1/providers", json=body)
    assert resp.status_code == 400, f"期望 400，实际 {resp.status_code}: {resp.text}"
    err = resp.json().get("error") or {}
    assert err.get("code") == "invalid_request", f"error.code != 'invalid_request': {err}"
    assert err.get("param") == "secret_ref", f"error.param != 'secret_ref': {err}"
