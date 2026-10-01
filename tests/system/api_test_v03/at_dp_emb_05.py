"""Case ID: ST-EMB-005

Endpoint: POST /v1/embeddings
Upstream Provider: m5air OMLX (bge-m3)
Model: Embedding-v1
Auth: Bearer dev-data

目标：验证 embedding batch size 超过 embedding_max_batch_inputs（32）时的行为。

断言（对齐 OpenAPI EmbeddingResponse，additionalProperties:false）：
- HTTP 200（LLMTier 层不校验 batch_size 上限；embeds 直发给上游）
- body 顶层键集恰 {object,data,model,usage}；object=="list"；model 回显
- data 恰 33 项；data[i].object=="embedding"、index==i、embedding 为 1024 维有限数值

注：registry.py:16 `embedding_max_batch_inputs` 是 informational 字段，
不体现在 embeddings.py 的 create() 校验逻辑中。
"""
from __future__ import annotations

import math

import pytest

from tests.system.api_test_v03.conftest import request_with_retry

TOP_KEYS = {"object", "data", "model", "usage"}


@pytest.mark.api_a
def test_dp_emb_05_batch_size_exceeded(api_client):
    # Evidence anchor: the tier declares a batch cap of 32...
    model_resp = api_client.get("/v1/models/Embedding-v1")
    if model_resp.status_code == 200:
        caps = (model_resp.json() or {}).get("capabilities") or {}
        assert caps.get("embedding_max_batch_inputs") == 32, (
            f"Embedding-v1 声明 batch 上限应为 32: {caps.get('embedding_max_batch_inputs')}"
        )

    body = {"model": "Embedding-v1", "input": ["hello"] * 33}
    resp = request_with_retry(api_client, "POST", "/v1/embeddings", json=body)
    assert resp.status_code == 200, f"期望 200，实际 {resp.status_code}: {resp.text}"
    data = resp.json()
    assert set(data) == TOP_KEYS, f"顶层键集不符: {sorted(data)}"
    assert data["object"] == "list", f"object != 'list': {data['object']!r}"
    assert data["model"] == "Embedding-v1", f"model 未回显: {data['model']!r}"
    items = data["data"]
    assert len(items) == 33, f"期望 33 个 embedding，实际 {len(items)}"
    for i, item in enumerate(items):
        assert item.get("object") == "embedding", f"data[{i}].object != 'embedding': {item}"
        assert item.get("index") == i, f"data[{i}].index != {i}: {item.get('index')!r}"
        emb = item.get("embedding")
        assert isinstance(emb, list) and len(emb) == 1024, (
            f"data[{i}] embedding 形状不符: {type(emb).__name__} len={len(emb) if isinstance(emb, list) else 'n/a'}"
        )
        assert all(math.isfinite(v) and not isinstance(v, bool) for v in emb), (
            f"data[{i}] 含非有限值/bool"
        )
