"""Case ID: ST-EMB-007

Endpoint: POST /v1/embeddings
Upstream Provider: 无（本地立即拒绝，不触上游）
Model: Embedding-v1（指向 embeddings-capable 部署 dep_local_bge_m3）
Auth: Bearer dev-data

目标：encoding_format="hex"（enum 仅 float|base64）→ 400 invalid_request
（param="encoding_format"），dispatch 前拒绝。

实现：src/inference/embeddings.py:34
  require(encoding in {"float","base64"}, 400, "invalid_request",
          "encoding_format must be one of: float, base64", "encoding_format")

断言：
- 主：HTTP 400 + code "invalid_request" + param "encoding_format"
- 加强负向（系统 §7.8 ERR-REQ-VALIDATION/ERR-REQ-FIELD）：
  - 缺 input → 400 invalid_request、param "input"
  - 缺 model → 400 invalid_request、param "model"
  - 未知顶层键 → 400 unsupported_field、param 为未知键名
"""
from __future__ import annotations

import pytest

ERROR_KEYS = {"message", "type", "code", "param", "retryable"}


@pytest.mark.api_a
def test_dp_emb_07_invalid_encoding_format(api_client):
    resp = api_client.post(
        "/v1/embeddings",
        json={"model": "Embedding-v1", "input": "Hello world", "encoding_format": "hex"},
    )
    assert resp.status_code == 400, f"期望 400，实际 {resp.status_code}: {resp.text}"
    assert resp.headers.get("content-type", "").startswith("application/json")
    body = resp.json()
    assert "object" not in body and "data" not in body, f"错误响应不应含成功字段: {body}"
    err = body.get("error") or {}
    assert err.get("code") == "invalid_request", f"error.code 不符: {err}"
    assert err.get("param") == "encoding_format", f"error.param 非 'encoding_format': {err}"
    assert err.get("type") == "request_error", f"error.type 不符: {err}"
    assert err.get("retryable") is False, f"error.retryable 非 False: {err}"
    assert set(err) == ERROR_KEYS, f"error 键集不符: {sorted(err)}"


@pytest.mark.api_a
@pytest.mark.parametrize(
    "body,code,param",
    [
        ({"model": "Embedding-v1"}, "invalid_request", "input"),
        ({"input": "Hello world"}, "invalid_request", "model"),
        ({"model": "Embedding-v1", "input": "Hello world", "foo": 1}, "unsupported_field", "foo"),
    ],
    ids=["missing-input", "missing-model", "unknown-key"],
)
def test_dp_emb_07_adjacent_invalid_request(api_client, body, code, param):
    resp = api_client.post("/v1/embeddings", json=body)
    assert resp.status_code == 400, f"期望 400，实际 {resp.status_code}: {resp.text}"
    err = resp.json().get("error") or {}
    assert err.get("code") == code, f"error.code 不符: {err}"
    assert err.get("param") == param, f"error.param 应为首个非法字段 {param!r}: {err}"
    assert err.get("type") == "request_error", f"error.type 不符: {err}"
    assert err.get("retryable") is False, f"error.retryable 非 False: {err}"
    assert set(err) == ERROR_KEYS, f"error 键集不符: {sorted(err)}"
