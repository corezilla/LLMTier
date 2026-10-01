"""Case ID: ST-resp-017

Endpoint: POST /v1/responses
Upstream Provider: 无（能力门在 dispatch 前拒绝）
Model: Embedding-v1（embedding-only，capabilities.responses == false）
Auth: Bearer dev-data

目标：embedding-only 等级发 Responses → 400 unsupported_model（param="model"），
不触上游。

实现：src/inference/responses.py:84
  require(caps.get("responses") is True, 400, "unsupported_model",
          "Selected model does not support Responses", "model")

断言：
- HTTP 400
- error.code == "unsupported_model"、param == "model"
- type == "request_error"、retryable is False、键集恰 5 键
"""
from __future__ import annotations

import pytest

ERROR_KEYS = {"message", "type", "code", "param", "retryable"}


@pytest.mark.api_a
def test_dp_resp_17_embedding_only_tier_rejected(api_client):
    resp = api_client.post(
        "/v1/responses",
        json={
            "model": "Embedding-v1",
            "input": [{"role": "user", "content": "hi"}],
            "stream": True,
            "store": False,
        },
    )
    assert resp.status_code == 400, f"期望 400，实际 {resp.status_code}: {resp.text}"
    assert resp.headers.get("content-type", "").startswith("application/json")
    err = resp.json().get("error") or {}
    assert err.get("code") == "unsupported_model", f"error.code 不符: {err}"
    assert err.get("param") == "model", f"error.param 非 'model': {err}"
    assert err.get("type") == "request_error", f"error.type 不符: {err}"
    assert err.get("retryable") is False, f"error.retryable 非 False: {err}"
    assert set(err) == ERROR_KEYS, f"error 键集不符: {sorted(err)}"
