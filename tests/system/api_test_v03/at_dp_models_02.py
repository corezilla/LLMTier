"""Case ID: ST-model-002

Endpoint: GET /v1/models/Worker
Upstream Provider: 无
Model: Worker
Auth: Bearer dev-data

断言：
- HTTP 200，Content-Type: application/json；存在 X-Request-ID
- body 键集恰 {id, object, created, owned_by, availability, capabilities}
- body.id == "Worker"、object == "model"、owned_by == "llmtier"
- created 是正整数（unix 秒）；availability ∈ 枚举；capabilities 为对象
- 交叉核对：与 GET /v1/models 中 id=="Worker" 的元素逐字段比对
  （id/object/owned_by/capabilities；created 按响应时刻生成，不参与比对）
"""
from __future__ import annotations

import pytest

MODEL_KEYS = {"id", "object", "created", "owned_by", "availability", "capabilities"}
AVAILABILITY = {"available", "degraded", "unavailable"}


@pytest.mark.api_a
def test_dp_models_02_get_worker(api_client):
    resp = api_client.get("/v1/models/Worker")
    assert resp.status_code == 200, f"GET /v1/models/Worker 返回 {resp.status_code}: {resp.text}"
    assert resp.headers.get("content-type", "").startswith("application/json")
    assert resp.headers.get("X-Request-ID"), f"缺 X-Request-ID: {dict(resp.headers)}"

    body = resp.json()
    assert set(body.keys()) == MODEL_KEYS, (
        f"Model 键集不符: missing={sorted(MODEL_KEYS - set(body.keys()))}, "
        f"extra={sorted(set(body.keys()) - MODEL_KEYS)}"
    )
    assert body["id"] == "Worker", f"id != 'Worker': {body}"
    assert body["object"] == "model", f"object != 'model': {body}"
    assert body["owned_by"] == "llmtier", f"owned_by != 'llmtier': {body}"
    created = body["created"]
    assert isinstance(created, int) and not isinstance(created, bool) and created > 0, (
        f"created 非正整数: {created}"
    )
    assert body["availability"] in AVAILABILITY, f"availability 非法: {body['availability']}"
    assert isinstance(body["capabilities"], dict), f"capabilities 非对象: {body}"

    # 独立交叉核对：单模型读取与清单成员是同一 Registry 视图（created 除外）。
    listing = api_client.get("/v1/models")
    assert listing.status_code == 200, f"/v1/models 返回 {listing.status_code}: {listing.text}"
    member = next((m for m in listing.json()["data"] if m["id"] == "Worker"), None)
    assert member is not None, "Worker 不在 /v1/models 清单中"
    for field in ("id", "object", "owned_by", "capabilities"):
        assert body[field] == member[field], (
            f"交叉核对字段 {field} 不一致: 单模型={body[field]!r} 清单={member[field]!r}"
        )
