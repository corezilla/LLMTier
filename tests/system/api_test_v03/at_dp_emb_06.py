"""Case ID: DP-EMB-06

Endpoint: POST /v1/embeddings
Upstream Provider: 无（本地立即拒绝，不触上游）
Model: Embedding-v1（冻结向量空间 bge-m3-dense-1024-v1，embedding_dimensions=[1024]）
Auth: Bearer dev-data

目标：dimensions=768 与冻结空间 [1024] 不符 → 400 unsupported_dimensions
（param="dimensions"），dispatch 前拒绝。

实现：src/inference/embeddings.py:42-43
  require(body["dimensions"] in caps["embedding_dimensions"], 400,
          "unsupported_dimensions", "Unsupported embedding dimensions", "dimensions")

断言：
- HTTP 400
- error.code == "unsupported_dimensions"、param == "dimensions"
- type == "request_error"、retryable is False、键集恰 5 键
"""
from __future__ import annotations

import pytest

ERROR_KEYS = {"message", "type", "code", "param", "retryable"}


@pytest.mark.api_a
def test_dp_emb_06_dimensions_not_in_frozen_space(api_client):
    model_resp = api_client.get("/v1/models/Embedding-v1")
    if model_resp.status_code == 200:
        caps = (model_resp.json() or {}).get("capabilities") or {}
        assert 768 not in (caps.get("embedding_dimensions") or []), (
            f"Embedding-v1 冻结空间不应包含 768: {caps.get('embedding_dimensions')}"
        )

    resp = api_client.post(
        "/v1/embeddings",
        json={"model": "Embedding-v1", "input": "Hello world", "dimensions": 768},
    )
    assert resp.status_code == 400, f"期望 400，实际 {resp.status_code}: {resp.text}"
    assert resp.headers.get("content-type", "").startswith("application/json")
    body = resp.json()
    assert "object" not in body and "data" not in body, f"错误响应不应含成功字段: {body}"
    err = body.get("error") or {}
    assert err.get("code") == "unsupported_dimensions", f"error.code 不符: {err}"
    assert err.get("param") == "dimensions", f"error.param 非 'dimensions': {err}"
    assert err.get("type") == "request_error", f"error.type 不符: {err}"
    assert err.get("retryable") is False, f"error.retryable 非 False: {err}"
    assert set(err) == ERROR_KEYS, f"error 键集不符: {sorted(err)}"
