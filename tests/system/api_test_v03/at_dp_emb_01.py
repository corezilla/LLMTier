"""Case ID: DP-EMB-01

Endpoint: POST /v1/embeddings
Upstream Provider: provider_local (m5air OMLX bge-m3)
Model: Embedding-v1 (backend: bge-m3)
Auth: Bearer dev-data

断言：
- HTTP 200
- body.data[0].embedding 长度 = 1024（bge-m3 硬编码）
- 所有值 finite（无 NaN/Inf）
- body.data[0].object == "embedding"
"""
from __future__ import annotations

import math

import pytest


@pytest.mark.api_a
def test_dp_emb_01_basic_embedding_1024(api_client):
    resp = api_client.post(
        "/v1/embeddings",
        json={"model": "Embedding-v1", "input": "Hello world"},
    )
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    data = body.get("data") or []
    assert data, f"data 为空: {body}"
    item = data[0]
    assert item.get("object") == "embedding", f"data[0].object != 'embedding': {item}"

    emb = item.get("embedding")
    assert isinstance(emb, list), f"embedding 非 list: {type(emb).__name__}"
    assert len(emb) == 1024, f"embedding 维数 = {len(emb)}，期望 1024"

    assert all(isinstance(v, (int, float)) for v in emb), "embedding 含非数值"
    assert all(math.isfinite(v) for v in emb), "embedding 含 NaN/Inf"
