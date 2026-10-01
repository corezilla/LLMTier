"""Case ID: ST-PROV-006

Endpoint: PATCH /v1/providers/{id}
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

前置条件：已有 provider（来自测试内创建）

断言：
- PATCH 不带 If-Match header
- HTTP 412
- error.code == "version_conflict"；type=="request_error"；retryable is False
- error.current_version == version_before
- 零副作用：GET 回读 name/version/ETag 未变
- teardown（finally 强制）：DELETE 并以 GET 404 确认
"""
from __future__ import annotations

import uuid

import pytest

from tests.system.api_test_v03.constants import LAN_PROVIDER_ENDPOINT
from tests.system.api_test_v03.conftest import version_conflict_envelope


def _delete_provider(client, rid) -> None:
    got = client.get(f"/v1/providers/{rid}")
    if got.status_code == 404:
        return
    assert got.status_code == 200, f"teardown GET 失败: {got.status_code}: {got.text}"
    etag = got.headers.get("ETag")
    assert etag, "teardown GET 缺 ETag"
    deleted = client.delete(f"/v1/providers/{rid}", headers={"If-Match": etag})
    assert deleted.status_code == 204, f"teardown DELETE 期望 204，实际 {deleted.status_code}: {deleted.text}"
    assert client.get(f"/v1/providers/{rid}").status_code == 404, "teardown 后 provider 仍存在"


@pytest.mark.api_b
def test_adm_prov_06_patch_missing_if_match(admin_client_b):
    rid = None
    try:
        create_resp = admin_client_b.post("/v1/providers", json={
            "name": f"Provider For Patch Test {uuid.uuid4().hex[:8]}",
            "kind": "local",
            "endpoint": LAN_PROVIDER_ENDPOINT,
            "secret_ref": None,
            "enabled": True,
        })
        assert create_resp.status_code == 201
        created = create_resp.json()
        rid = created["id"]
        version_before = created["version"]
        etag_before = create_resp.headers["ETag"]

        patch_resp = admin_client_b.patch(
            f"/v1/providers/{rid}",
            json={"name": "Should Not Be Applied"},
        )
        assert patch_resp.status_code == 412, f"期望 412，实际 {patch_resp.status_code}: {patch_resp.text}"
        err = version_conflict_envelope(patch_resp)
        assert err["code"] == "version_conflict", f"error.code != version_conflict: {err}"
        assert err["type"] == "request_error", f"error.type != request_error: {err}"
        assert err["retryable"] is False, f"error.retryable != False: {err}"
        assert err.get("current_version") == version_before, (
            f"current_version 期望 {version_before}，实际 {err.get('current_version')!r}")

        readback = admin_client_b.get(f"/v1/providers/{rid}")
        assert readback.status_code == 200
        assert readback.json()["name"] == created["name"], "被拒 PATCH 却改了 name"
        assert readback.json()["version"] == version_before, "被拒 PATCH 却推进了 version"
        assert readback.headers.get("ETag") == etag_before, "被拒 PATCH 却改了 ETag"
    finally:
        if rid is not None:
            _delete_provider(admin_client_b, rid)
