"""Case ID: DP-EMB-05

Endpoint: POST /v1/embeddings
Upstream Provider: m5air OMLX (bge-m3)
Model: Embedding-v1
Auth: Bearer dev-data

目标：验证 embedding batch size 超过 embedding_max_batch_inputs（32）时的行为。

断言：
- HTTP 200（LLMTier 层不校验 batch_size 上限；embeds 直发给上游）
- body.data 含 33 个 embedding 对象

注：registry.py:16 `embedding_max_batch_inputs` 是 informational 字段，
不体现在 embeddings.py 的 create() 校验逻辑中。
capabilities 只用于 /v1/models 响应中的元数据展示。
实际 batch 限制由上游 bge-m3 自行处理。
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_dp_emb_05_batch_size_exceeded(api_client):
    body = {
        "model": "Embedding-v1",
        "input": ["hello"] * 33,
    }
    resp = api_client.post("/v1/embeddings", json=body)
    assert resp.status_code == 200, f"期望 200，实际 {resp.status_code}: {resp.text}"
    data = resp.json()
    assert "data" in data
    assert len(data["data"]) == 33, f"期望 33 个 embedding，实际 {len(data['data'])}"
