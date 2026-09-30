"""Case ID: DP-EMB-01

Endpoint: POST /v1/embeddings
Upstream Provider: provider_local (m5air OMLX bge-m3)
Model: Embedding-v1 (backend: bge-m3)
Auth: Bearer dev-data

断言（对齐 OpenAPI EmbeddingResponse/EmbeddingItem, additionalProperties:false）：
- HTTP 200；content-type application/json；非错误信封
- 顶层键集恰为 {object,data,model,usage}；object == "list"；model == "Embedding-v1"（逻辑模型回显）
- data[0] 键集恰为 {object,index,embedding}；object == "embedding"；index == 0
- embedding 为 1024 个有限数值；**元素非 bool**（bool ⊂ int，须显式排除）
"""
from __future__ import annotations

import math

import pytest

from tests.system.api_test_v03.conftest import request_with_retry

TOP_KEYS = {"object", "data", "model", "usage"}
ITEM_KEYS = {"object", "index", "embedding"}


@pytest.mark.api_a
def test_dp_emb_01_basic_embedding_1024(api_client):
    resp = request_with_retry(
        api_client,
        "POST",
        "/v1/embeddings",
        json={"model": "Embedding-v1", "input": "Hello world"},
    )
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    assert resp.headers.get("content-type", "").startswith("application/json")
    body = resp.json()
    assert "error" not in body, f"成功响应不应含 error: {body}"

    assert set(body) == TOP_KEYS, f"顶层键集不符，期望 {sorted(TOP_KEYS)}: {sorted(body)}"
    assert body["object"] == "list", f"object != 'list': {body['object']!r}"
    assert body["model"] == "Embedding-v1", f"model 未回显逻辑模型: {body['model']!r}"

    data = body.get("data") or []
    assert data, f"data 为空: {body}"
    item = data[0]
    assert set(item) == ITEM_KEYS, f"data[0] 键集不符: {sorted(item)}"
    assert item.get("object") == "embedding", f"data[0].object != 'embedding': {item}"
    assert item.get("index") == 0, f"data[0].index != 0: {item.get('index')!r}"

    emb = item.get("embedding")
    assert isinstance(emb, list), f"embedding 非 list: {type(emb).__name__}"
    assert len(emb) == 1024, f"embedding 维数 = {len(emb)}，期望 1024"

    assert all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in emb), (
        "embedding 含非数值或 bool"
    )
    assert all(math.isfinite(v) for v in emb), "embedding 含 NaN/Inf"
