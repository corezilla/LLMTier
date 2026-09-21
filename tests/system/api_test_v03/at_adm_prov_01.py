"""Case ID: ADM-PROV-01

Endpoint: GET /tier/admin/v1/providers
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 200
- body.data[] 含已知 3 个核心 provider（provider_minimax, provider_local, provider_omlx_m5mac）
- body.page.has_more 为 boolean

注：m5air 经多轮 B-class 测试后实际有 16 个 provider（超过默认 limit=10），
因此 has_more 可能为 True，不强断言。
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
    assert not missing, f"缺 provider: {sorted(missing)}（实际 ids: {sorted(ids)}）"
    page = body.get("page") or {}
    assert isinstance(page.get("has_more"), bool), f"page.has_more 不是 boolean: {page}"
