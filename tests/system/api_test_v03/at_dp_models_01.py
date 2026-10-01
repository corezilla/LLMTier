"""Case ID: ST-model-001

Endpoint: GET /v1/models
Upstream Provider: 无
Model: 无
Auth: Bearer dev-data

断言：
- HTTP 200，Content-Type: application/json；存在 X-Request-ID
- 顶层键集恰 {object, data}，body.object == "list"，body.data 为数组
- body.data 恰为 7 个 FIXED_TIERS（无缺无多），id 唯一
- 逐元素键集恰 {id, object, created, owned_by, availability, capabilities}
  且 object=="model"、owned_by=="llmtier"、created 为正整数、
  availability ∈ {available,degraded,unavailable}、capabilities 为对象
"""
from __future__ import annotations

from tests.system.api_test_v03.constants import FIXED_TIERS

import pytest

MODEL_KEYS = {"id", "object", "created", "owned_by", "availability", "capabilities"}
AVAILABILITY = {"available", "degraded", "unavailable"}


@pytest.mark.api_a
def test_dp_models_01_list_contains_7_tiers(api_client):
    resp = api_client.get("/v1/models")
    assert resp.status_code == 200, f"/v1/models 返回 {resp.status_code}: {resp.text}"
    assert resp.headers.get("content-type", "").startswith("application/json")
    assert resp.headers.get("X-Request-ID"), f"缺 X-Request-ID: {dict(resp.headers)}"

    body = resp.json()
    assert set(body.keys()) == {"object", "data"}, (
        f"ModelList 顶层键集不符（期望恰 {{object, data}}）: {sorted(body.keys())}"
    )
    assert body["object"] == "list", f"object != 'list': {body}"
    data = body["data"]
    assert isinstance(data, list), f"data 非数组: {type(data)}"

    ids = [m["id"] for m in data]
    assert len(ids) == len(set(ids)), f"id 不唯一: {ids}"
    assert len(data) == len(FIXED_TIERS), f"期望 {len(FIXED_TIERS)} 个 model，实际 {len(data)}: {ids}"
    assert set(ids) == set(FIXED_TIERS), (
        f"model 集合不符: missing={sorted(set(FIXED_TIERS) - set(ids))}, "
        f"extra={sorted(set(ids) - set(FIXED_TIERS))}"
    )

    for m in data:
        tier_id = m.get("id", "?")
        assert set(m.keys()) == MODEL_KEYS, (
            f"tier {tier_id} 元素键集不符: "
            f"missing={sorted(MODEL_KEYS - set(m.keys()))}, extra={sorted(set(m.keys()) - MODEL_KEYS)}"
        )
        assert m["object"] == "model", f"tier {tier_id} object != 'model': {m}"
        assert m["owned_by"] == "llmtier", f"tier {tier_id} owned_by != 'llmtier': {m}"
        created = m["created"]
        assert isinstance(created, int) and not isinstance(created, bool) and created > 0, (
            f"tier {tier_id} created 非正整数: {created}"
        )
        assert m["availability"] in AVAILABILITY, (
            f"tier {tier_id} availability 非法: {m['availability']}"
        )
        assert isinstance(m["capabilities"], dict), f"tier {tier_id} capabilities 非对象: {m}"
