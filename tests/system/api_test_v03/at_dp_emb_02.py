"""Case ID: DP-EMB-02

Endpoint: POST /v1/embeddings (encoding_format=base64)
Upstream Provider: provider_local (m5air OMLX bge-m3)
Model: Embedding-v1 (backend: bge-m3)
Auth: Bearer dev-data

断言：
- HTTP 200
- body.data[0].embedding 是 base64 字符串
- 解码后 1024 个 little-endian float32
- 全部 finite
"""
from __future__ import annotations

import base64
import math
import struct

import pytest


@pytest.mark.api_a
def test_dp_emb_02_base64_decodes_to_1024_float32(api_client):
    resp = api_client.post(
        "/v1/embeddings",
        json={"model": "Embedding-v1", "input": "Hello world", "encoding_format": "base64"},
    )
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    item = (body.get("data") or [{}])[0]
    emb = item.get("embedding")
    assert isinstance(emb, str), f"embedding 非字符串: {type(emb).__name__}"

    raw = base64.b64decode(emb)
    n = len(raw) // 4
    assert n == 1024, f"base64 解码后 float32 数 = {n}，期望 1024"

    arr = struct.unpack(f"<{n}f", raw)
    assert all(math.isfinite(v) for v in arr), "float32 含 NaN/Inf"
