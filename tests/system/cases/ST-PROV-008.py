"""Case ID: ST-PROV-008

Endpoint: DELETE /v1/providers/{id}
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

前置条件：已有 provider（独立创建）

断言：
- DELETE 带正确 If-Match
- HTTP 204（空 body）
- 随后 GET 返回 404 且 error.code == "not_found"
"""
from __future__ import annotations

import uuid

import pytest

from tests.system.constants import LAN_PROVIDER_ENDPOINT
from tests.system.conftest import error_envelope


@pytest.mark.api_b
def test_adm_prov_08_delete_provider(admin_client_b):
    create_resp = admin_client_b.post("/v1/providers", json={
        "name": f"Provider To Delete {uuid.uuid4().hex[:8]}",
        "kind": "local",
        "endpoint": LAN_PROVIDER_ENDPOINT,
        "secret_ref": None,
        "enabled": True,
    })
    assert create_resp.status_code == 201
    rid = create_resp.json()["id"]
    etag = create_resp.headers["ETag"]

    del_resp = admin_client_b.delete(
        f"/v1/providers/{rid}",
        headers={"If-Match": etag},
    )
    assert del_resp.status_code == 204, f"期望 204，实际 {del_resp.status_code}: {del_resp.text}"
    assert del_resp.content == b"", f"204 响应体应为空，实际 {del_resp.content!r}"

    get_resp = admin_client_b.get(f"/v1/providers/{rid}")
    assert get_resp.status_code == 404, f"期望 404，实际 {get_resp.status_code}"
    assert error_envelope(get_resp)["code"] == "not_found", "删除后 GET 应 404 not_found"
