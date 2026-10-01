"""Case ID: ST-PROV-001

Endpoint: GET /v1/providers
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 200
- body.page 键集恰为 {has_more, next_cursor}；has_more 为 boolean，next_cursor 为 string|null
- body.data[] 含已知 3 个核心 provider（provider_minimax, provider_local, provider_omlx_m5mac）
- 每个元素键集恰为 ProviderView 9 键

注：GET /v1/providers 默认 limit=100（app.py `_int_param(query,"limit",100)`）；
本 case 不带 limit，走默认分页。m5air 经历史 B-class 测试后 provider 可能 >100
时 has_more 才为 True；本 case 只断言类型/结构，不强断言具体布尔值。
"""
from __future__ import annotations

import pytest

PROVIDER_VIEW_KEYS = {
    "id", "name", "kind", "endpoint", "has_secret",
    "enabled", "usage", "request_usage", "version",
}


@pytest.mark.api_a
def test_adm_prov_01_list_providers(admin_client):
    resp = admin_client.get("/v1/providers")
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    data = body.get("data") or []
    ids = {p.get("id") for p in data}
    expected = {"provider_minimax", "provider_local", "provider_omlx_m5mac"}
    missing = expected - ids
    assert not missing, f"缺 provider: {sorted(missing)}（实际 ids: {sorted(ids)}）"

    page = body.get("page")
    assert isinstance(page, dict), f"page 非对象: {page!r}"
    assert set(page) == {"has_more", "next_cursor"}, (
        f"page 键集不符（additionalProperties:false）: {set(page)}")
    assert isinstance(page["has_more"], bool), f"page.has_more 不是 boolean: {page}"
    assert page["next_cursor"] is None or isinstance(page["next_cursor"], str), (
        f"page.next_cursor 非 string|null: {page['next_cursor']!r}")

    for item in data:
        assert isinstance(item, dict), f"data 元素非对象: {item!r}"
        assert set(item) == PROVIDER_VIEW_KEYS, (
            f"ProviderView 键集不符: {set(item)} != {PROVIDER_VIEW_KEYS}")
