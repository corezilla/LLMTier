"""Case ID: ADM-DEPL-09

Endpoint: PATCH /v1/deployments/{id}
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

目标：验证 deployment 的 provider_id 不可随意更改（更换为不存在 provider → 400）。

断言：
- HTTP 400
- error.code == "invalid_request"
"""
from __future__ import annotations

import pytest

BASELINE_PROVIDER_ID = "prov_b"


@pytest.mark.api_b
def test_adm_depl_09_provider_id_immutable(admin_client_b):
    depl_resp = admin_client_b.get("/v1/deployments/depl_b")
    assert depl_resp.status_code == 200
    etag = depl_resp.headers.get("ETag")

    patch_resp = admin_client_b.patch(
        "/v1/deployments/depl_b",
        json={"provider_id": "nonexistent_provider"},
        headers={"If-Match": etag},
    )
    assert patch_resp.status_code == 400, f"期望 400，实际 {patch_resp.status_code}: {patch_resp.text}"
    err = patch_resp.json().get("error") or {}
    assert err.get("code") == "invalid_request"
