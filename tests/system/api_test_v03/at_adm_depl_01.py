"""Case ID: ADM-DEPL-01

Endpoint: GET /v1/deployments
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 200
- body.data[] 含 m5air 现有 4 个 deployment
- body.page 键集恰为 {has_more, next_cursor}；has_more 为 JSON 布尔，next_cursor 为 string|null
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_adm_depl_01_list_deployments(admin_client):
    resp = admin_client.get("/v1/deployments")
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    data = body.get("data") or []

    page = body.get("page")
    assert isinstance(page, dict), f"缺 page 对象: {list(body.keys())}"
    assert set(page) == {"has_more", "next_cursor"}, f"page 键集不符: {set(page)}"
    assert isinstance(page["has_more"], bool), (
        f"page.has_more 非 JSON 布尔: {type(page['has_more']).__name__}")
    assert page["next_cursor"] is None or isinstance(page["next_cursor"], str), (
        f"page.next_cursor 非 string/null: {type(page['next_cursor']).__name__}")

    ids = {d.get("id") for d in data}
    expected = {"dep_local_gemma", "dep_local_bge_m3", "dep_omlx_qwen36", "dep_minimax_m27"}
    missing = expected - ids
    assert not missing, f"缺 deployment: {sorted(missing)}（实际: {ids}）"
