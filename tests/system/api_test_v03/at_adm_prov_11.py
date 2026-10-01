"""Case ID: ST-prov-011

Endpoint: POST /v1/providers
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

目标：验证 kind 字段枚举校验；无效值 → 400。

断言：
- HTTP 400
- error.code == "invalid_request"
- error.param == "kind"（区分性断言：400 由 kind 字段触发）
- 5 键信封：type=="request_error"、retryable is False
- 零副作用：provider 集合与请求前一致
"""
from __future__ import annotations

import uuid

import pytest

from tests.system.api_test_v03.constants import LAN_PROVIDER_ENDPOINT
from tests.system.api_test_v03.conftest import error_envelope


@pytest.mark.api_b
def test_adm_prov_11_kind_enum_validation(admin_client_b):
    before_ids = {
        p["id"] for p in admin_client_b.get("/v1/providers?limit=200").json()["data"]
    }
    body = {
        "name": f"Test Provider {uuid.uuid4().hex[:8]}",
        "kind": "invalid_kind",
        "endpoint": LAN_PROVIDER_ENDPOINT,
        "secret_ref": None,
        "enabled": True,
    }
    resp = admin_client_b.post("/v1/providers", json=body)
    assert resp.status_code == 400, f"期望 400，实际 {resp.status_code}: {resp.text}"
    err = error_envelope(resp)
    assert err["code"] == "invalid_request", f"error.code != 'invalid_request': {err}"
    assert err["param"] == "kind", f"error.param 期望 'kind'，实际 {err.get('param')!r}"
    assert err["type"] == "request_error", f"error.type != 'request_error': {err}"
    assert err["retryable"] is False, f"error.retryable != False: {err}"

    after_ids = {
        p["id"] for p in admin_client_b.get("/v1/providers?limit=200").json()["data"]
    }
    assert after_ids == before_ids, "被拒创建却出现 provider 资源副作用"
