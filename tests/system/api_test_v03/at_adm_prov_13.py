"""Case ID: ADM-PROV-13

Endpoint: PATCH /v1/providers/{id}
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

目标：验证 usage 子对象更新（max_concurrent_requests）。

断言：
- HTTP 200
- 更新后 GET 能读到新值
"""
from __future__ import annotations

import pytest


@pytest.mark.api_b
def test_adm_prov_13_usage_subobject_update(admin_client_b):
    current = admin_client_b.get("/v1/providers/prov_b")
    assert current.status_code == 200, f"GET prov_b 失败: {current.status_code}: {current.text}"
    etag = current.headers.get("ETag")
    assert etag, "GET prov_b 缺 ETag"
    original = current.json().get("usage", {}).get("max_concurrent_requests")

    try:
        patch_resp = admin_client_b.patch(
            "/v1/providers/prov_b",
            json={"usage": {"max_concurrent_requests": 5}},
            headers={"If-Match": etag},
        )
        assert patch_resp.status_code == 200, f"期望 200，实际 {patch_resp.status_code}: {patch_resp.text}"

        get_resp = admin_client_b.get("/v1/providers/prov_b")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data.get("usage", {}).get("max_concurrent_requests") == 5
    finally:
        # Restore the original value so later cases see the baseline provider.
        restore = admin_client_b.get("/v1/providers/prov_b")
        if restore.status_code == 200 and original is not None:
            if restore.json().get("usage", {}).get("max_concurrent_requests") != original:
                admin_client_b.patch(
                    "/v1/providers/prov_b",
                    json={"usage": {"max_concurrent_requests": original}},
                    headers={"If-Match": restore.headers["ETag"]},
                )
