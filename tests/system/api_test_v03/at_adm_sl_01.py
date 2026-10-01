"""Case ID: ST-SL-001

Endpoint: GET /v1/service-levels
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

断言：
- HTTP 200
- body 键集恰为 {data, page}；page 键集恰为 {has_more, next_cursor}
- body.data 为 ServiceLevelView[]（元素键集恰 5 键；enabled bool；version int ≥1；capabilities 12 键）
- body.data[] 含 7 个 FIXED_TIERS（Senior/Junior/Worker/Associate/Engineer/Executor/Embedding-v1）
"""
from __future__ import annotations

from tests.system.api_test_v03.constants import FIXED_TIERS

import pytest

SERVICE_LEVEL_VIEW_KEYS = {"id", "deployment_ids", "enabled", "capabilities", "version"}
CAPABILITY_KEYS = {
    "responses", "embeddings", "tools", "structured_outputs", "input_modalities",
    "output_modalities", "context_window", "max_output_tokens", "embedding_space_id",
    "embedding_dimensions", "embedding_max_batch_inputs", "embedding_max_input_tokens",
}


@pytest.mark.api_a
def test_adm_sl_01_list_service_levels(admin_client):
    resp = admin_client.get("/v1/service-levels")
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    assert set(body) == {"data", "page"}, f"ServiceLevelPage 键集不符: {set(body)}"
    assert isinstance(body["data"], list), f"data 非数组: {type(body['data']).__name__}"
    data = body["data"]

    page = body["page"]
    assert isinstance(page, dict), f"缺 page 对象: {list(body.keys())}"
    assert set(page) == {"has_more", "next_cursor"}, f"page 键集不符: {set(page)}"
    assert isinstance(page["has_more"], bool), (
        f"page.has_more 非 JSON 布尔: {type(page['has_more']).__name__}")
    assert page["next_cursor"] is None or isinstance(page["next_cursor"], str), (
        f"page.next_cursor 非 string/null: {type(page['next_cursor']).__name__}")

    for s in data:
        assert set(s) == SERVICE_LEVEL_VIEW_KEYS, f"ServiceLevelView 键集不符: {set(s)}"
        assert isinstance(s["deployment_ids"], list), f"deployment_ids 非数组: {s['deployment_ids']!r}"
        assert isinstance(s["enabled"], bool), f"enabled 非布尔: {s['enabled']!r}"
        assert isinstance(s["version"], int) and s["version"] >= 1, (
            f"version 非 int≥1: {s['version']!r}")
        assert set(s["capabilities"]) == CAPABILITY_KEYS, (
            f"{s['id']} capabilities 键集不符: {set(s['capabilities'])}")

    ids = {s.get("id") for s in data}
    missing = set(FIXED_TIERS) - ids
    assert not missing, f"缺 service level: {sorted(missing)}（实际: {ids}）"
    assert ids == set(FIXED_TIERS), f"列表应仅含 7 个固定 Tier，实际: {ids}"
