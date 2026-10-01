"""Case ID: ST-prov-005

Endpoint: PATCH /v1/providers/{id}
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

依赖：先创建一个 provider（由 ST-prov-002 创建，或本 case 自创）

断言：
- HTTP 200
- body 含更新后的 provider
- version == 创建 version + 1（精确，不是 >）
- 新 ETag == "<rid>.v<new>"
- GET 回读：新值持久化、ETag 一致
- teardown（finally 强制）：DELETE 并以 GET 404 确认
"""
from __future__ import annotations

import uuid

import pytest

from tests.system.api_test_v03.constants import LAN_PROVIDER_ENDPOINT


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
def test_adm_prov_05_update_provider(admin_client_b):
    rid = None
    try:
        create_resp = admin_client_b.post("/v1/providers", json={
            "name": f"Provider To Update {uuid.uuid4().hex[:8]}",
            "kind": "cloud",
            "endpoint": LAN_PROVIDER_ENDPOINT,
            "secret_ref": None,
            "enabled": True,
        })
        assert create_resp.status_code == 201
        provider = create_resp.json()
        rid = provider["id"]
        original_version = provider["version"]
        original_etag = create_resp.headers["ETag"]
        assert original_etag == f'"{rid}.v{original_version}"'

        patch_resp = admin_client_b.patch(
            f"/v1/providers/{rid}",
            json={"name": "Provider Updated Name", "enabled": False},
            headers={"If-Match": original_etag},
        )
        assert patch_resp.status_code == 200, f"期望 200，实际 {patch_resp.status_code}: {patch_resp.text}"
        updated = patch_resp.json()
        assert updated["name"] == "Provider Updated Name"
        assert updated["enabled"] is False
        expected_version = original_version + 1
        assert updated["version"] == expected_version, (
            f"version 期望 {expected_version}（原 {original_version}+1），实际 {updated['version']}")
        new_etag = patch_resp.headers.get("ETag")
        assert new_etag == f'"{rid}.v{expected_version}"', (
            f"新 ETag 期望 '\"{rid}.v{expected_version}\"', 实际 {new_etag!r}")

        get_resp = admin_client_b.get(f"/v1/providers/{rid}")
        assert get_resp.status_code == 200
        readback = get_resp.json()
        assert readback["name"] == "Provider Updated Name", "PATCH 未持久化"
        assert readback["enabled"] is False, "PATCH enabled 未持久化"
        assert readback["kind"] == "cloud", "未提交字段 kind 应保持原值"
        assert get_resp.headers.get("ETag") == new_etag, "回读 ETag 与新 ETag 不一致"
    finally:
        if rid is not None:
            _delete_provider(admin_client_b, rid)
