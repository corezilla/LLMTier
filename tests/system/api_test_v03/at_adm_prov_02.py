"""Case ID: ADM-PROV-02

Endpoint: POST /v1/providers
Upstream Provider: 无（测试 CRUD 路由，不测 upstream）
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 201
- body 含 provider 对象（id, name, kind, endpoint, enabled, version）
- version == 1；has_secret is False；响应体不含 secret_ref
- ETag response header == "<id>.v1"
- 可通过 GET /v1/providers/{id} 回读（同 name、同 ETag）
- teardown（finally 强制）：DELETE 并以 GET 404 确认

注：本 case 自建 self-clean（doc §4 step 6 / §6 强制 finally DELETE），不得向
session llmtier_b 泄漏 provider。
"""
from __future__ import annotations

import uuid

import pytest

from tests.system.api_test_v03.constants import LAN_PROVIDER_ENDPOINT


def _delete_provider(client, rid) -> None:
    """Teardown helper: GET fresh ETag then DELETE (204), tolerate already-gone."""
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
def test_adm_prov_02_create_provider(admin_client_b):
    body = {
        "name": f"Test Provider {uuid.uuid4().hex[:8]}",
        "kind": "local",
        "endpoint": LAN_PROVIDER_ENDPOINT,
        "secret_ref": None,
        "enabled": True,
    }
    rid = None
    try:
        resp = admin_client_b.post("/v1/providers", json=body)
        assert resp.status_code == 201, f"期望 201，实际 {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["name"] == body["name"]
        assert data["kind"] == body["kind"]
        assert data["endpoint"] == body["endpoint"]
        assert data["enabled"] == body["enabled"]
        assert "id" in data
        rid = data["id"]
        assert data["version"] == 1, f"创建初始 version 期望 1，实际 {data['version']!r}"
        assert data.get("has_secret") is False, f"secret_ref=null ⇒ has_secret=False，实际 {data.get('has_secret')!r}"
        assert "secret_ref" not in data, f"ProviderView 不得回显 secret_ref: {data}"
        assert "ETag" in resp.headers, "响应缺 ETag header"

        etag = resp.headers["ETag"]
        assert etag == f'"{rid}.v1"', f"ETag 期望 '\"{rid}.v1\"'，实际 {etag!r}"

        get_resp = admin_client_b.get(f"/v1/providers/{rid}")
        assert get_resp.status_code == 200
        assert get_resp.json()["name"] == body["name"]
        assert get_resp.json()["version"] == 1
        assert get_resp.headers.get("ETag") == etag
    finally:
        if rid is not None:
            _delete_provider(admin_client_b, rid)
