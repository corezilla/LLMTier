"""Case ID: ADM-PROV-01

Endpoint: GET /tier/admin/v1/providers
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 200
- body.data[] 含 m5air 现有 3 个 provider（provider_minimax, provider_local, provider_omlx_m5mac）
- body.page.has_more == False
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_adm_prov_01_list_providers(admin_client):
    resp = admin_client.get("/tier/admin/v1/providers")
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    data = body.get("data") or []
    ids = {p.get("id") for p in data}
    expected = {"provider_minimax", "provider_local", "provider_omlx_m5mac"}
    missing = expected - ids
    assert not missing, f"缺 provider: {sorted(missing)}（实际 ids: {ids}）"
    page = body.get("page") or {}
    assert page.get("has_more") is False, f"page.has_more 不为 False: {page}"
