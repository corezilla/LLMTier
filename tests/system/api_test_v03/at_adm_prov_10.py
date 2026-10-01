"""Case ID: ST-PROV-010

Endpoint: DELETE /v1/providers/{id}
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

前置条件：provider 有 active deployment（prov_b → depl_b，来自 baseline settings）

断言：
- DELETE 带正确 If-Match
- HTTP 409
- error.code == "resource_in_use"；type=="request_error"；retryable is False
- error.message 包含 "referenced"
- 保留证明：GET prov_b 仍 200 且 version/ETag 未变
"""
from __future__ import annotations

import pytest

from tests.system.api_test_v03.conftest import error_envelope


@pytest.mark.api_b
def test_adm_prov_10_delete_provider_with_active_deployment(admin_client_b):
    current = admin_client_b.get("/v1/providers/prov_b")
    assert current.status_code == 200, f"GET prov_b 失败: {current.status_code}: {current.text}"
    etag = current.headers.get("ETag")
    assert etag, "GET prov_b 缺 ETag"
    version_before = current.json()["version"]

    r = admin_client_b.delete(
        "/v1/providers/prov_b",
        headers={"If-Match": etag},
    )
    assert r.status_code == 409, f"期望 409，实际 {r.status_code}: {r.text}"
    err = error_envelope(r)
    assert err["code"] == "resource_in_use", f"error.code != resource_in_use: {err}"
    assert err["type"] == "request_error", f"error.type != request_error: {err}"
    assert err["retryable"] is False, f"error.retryable != False: {err}"
    assert "referenced" in err.get("message", "").lower(), f"message 未含 'referenced': {err}"

    retained = admin_client_b.get("/v1/providers/prov_b")
    assert retained.status_code == 200, "被 409 拒绝的 DELETE 却删除了 prov_b"
    assert retained.json()["version"] == version_before, "被拒 DELETE 却推进了 prov_b version"
    assert retained.headers.get("ETag") == etag, "被拒 DELETE 却改了 prov_b ETag"
