"""Case ID: DP-EMB-03

Endpoint: POST /v1/embeddings × 5
Upstream Provider: provider_local (m5air OMLX bge-m3)
Model: Embedding-v1
Auth: Bearer dev-data

断言：
- 5 次请求都 200
- 5 次 embedding 维度均为 1024
- 5 个向量两两 cosine similarity > 0.99（同输入，结果应高相似）
"""
from __future__ import annotations

import math

import pytest

from tests.system.api_test_v03.conftest import request_with_retry


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


@pytest.mark.api_a
def test_dp_emb_03_5x_invariant_cosine_high(api_client):
    vectors: list[list[float]] = []
    for i in range(5):
        resp = request_with_retry(
            api_client,
            "POST",
            "/v1/embeddings",
            json={"model": "Embedding-v1", "input": "Hello world"},
        )
        assert resp.status_code == 200, f"第 {i+1} 次返回 {resp.status_code}: {resp.text}"
        item = resp.json()["data"][0]
        assert item["object"] == "embedding", f"第 {i+1} 次 object != 'embedding': {item}"
        assert item["index"] == 0, f"第 {i+1} 次 index != 0: {item.get('index')!r}"
        emb = item["embedding"]
        assert isinstance(emb, list), f"第 {i+1} 次 embedding 非 list: {type(emb).__name__}"
        assert len(emb) == 1024, f"第 {i+1} 次维数 = {len(emb)}，期望 1024"
        assert all(
            isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
            for v in emb
        ), f"第 {i+1} 次 embedding 含非数值/bool/NaN/Inf"
        vectors.append(emb)

    for i in range(5):
        for j in range(i + 1, 5):
            sim = _cosine(vectors[i], vectors[j])
            assert sim > 0.99, f"cosine({i},{j}) = {sim} ≤ 0.99"
