"""Case ID: ST-emb-002

Endpoint: POST /v1/embeddings (encoding_format=base64)
Upstream Provider: provider_local (m5air OMLX bge-m3)
Model: Embedding-v1 (backend: bge-m3)
Auth: Bearer dev-data

断言（对齐 OpenAPI EmbeddingItem.embedding contentEncoding:base64, little-endian float32）：
- HTTP 200；顶层键集恰为 {object,data,model,usage}；object=="list"；model 回显
- data[0].object=="embedding"、index==0；embedding 为字符串（非 JSON 数组）
- 严格解码 base64.b64decode(emb, validate=True) 后 raw 恰 4096 字节 = 1024×4
- struct.unpack("<1024f") 得 1024 个 float32 且全部 finite
"""
from __future__ import annotations

import base64
import math
import struct

import pytest

from tests.system.api_test_v03.conftest import request_with_retry

TOP_KEYS = {"object", "data", "model", "usage"}


@pytest.mark.api_a
def test_dp_emb_02_base64_decodes_to_1024_float32(api_client):
    resp = request_with_retry(
        api_client,
        "POST",
        "/v1/embeddings",
        json={"model": "Embedding-v1", "input": "Hello world", "encoding_format": "base64"},
    )
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    assert resp.headers.get("content-type", "").startswith("application/json")
    body = resp.json()
    assert set(body) == TOP_KEYS, f"顶层键集不符: {sorted(body)}"
    assert body["object"] == "list", f"object != 'list': {body['object']!r}"
    assert body["model"] == "Embedding-v1", f"model 未回显逻辑模型: {body['model']!r}"

    data = body.get("data") or []
    assert data, f"data 为空: {body}"
    item = data[0]
    assert item.get("object") == "embedding", f"data[0].object != 'embedding': {item}"
    assert item.get("index") == 0, f"data[0].index != 0: {item.get('index')!r}"
    emb = item.get("embedding")
    assert isinstance(emb, str), f"embedding 非字符串: {type(emb).__name__}"

    raw = base64.b64decode(emb, validate=True)
    assert len(raw) == 4096, f"base64 解码后字节数 = {len(raw)}，期望 4096（1024×4）"

    arr = struct.unpack("<1024f", raw)
    assert len(arr) == 1024
    assert all(math.isfinite(v) for v in arr), "float32 含 NaN/Inf"
