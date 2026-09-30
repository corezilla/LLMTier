"""Case ID: DP-EMB-10

Endpoint: POST /v1/embeddings
Upstream Provider: prov_b（LAN fake provider，backend_model="force-503"）
Model: Senior（指向 depl_b）
Auth: Bearer dev-data

TS-002 依赖：
  Endpoint: 临时 LLMTier 实例（llmtier_b_emb_503），127.0.0.1:<临时端口>
  上游: LAN fake provider（fake_provider_b），对 model="force-503" 返回 503
  Auth: Bearer dev-data

目标：验证上游 5xx/不可用 → 503 provider_unavailable。

断言：
- HTTP 503
- error.code == "provider_unavailable"、type == "server_error"
- param is None、retryable is True、键集恰 5 键
- 无成功 data 载荷

实现：src/inference/providers/openai.py::_request
（HTTPError>=500 / URLError / TimeoutError / JSONDecodeError → 503）。
"""
from __future__ import annotations

import pytest

ERROR_KEYS = {"message", "type", "code", "param", "retryable"}


@pytest.mark.api_b
def test_dp_emb_10_upstream_unavailable_503(llmtier_b_emb_503):
    client = llmtier_b_emb_503.api_client()
    try:
        resp = client.post("/v1/embeddings", json={"model": "Senior", "input": "hello"})
    finally:
        client.close()

    assert resp.status_code == 503, f"期望 503，实际 {resp.status_code}: {resp.text}"
    assert resp.headers.get("content-type", "").startswith("application/json")
    body = resp.json()
    assert "data" not in body, f"上游不可用却流出成功载荷: {body}"
    err = body.get("error") or {}
    assert err.get("code") == "provider_unavailable", f"error.code 不符: {err}"
    assert err.get("type") == "server_error", f"error.type 不符: {err}"
    assert err.get("param") is None, f"error.param 非 null: {err}"
    assert err.get("retryable") is True, f"error.retryable 非 True: {err}"
    assert set(err) == ERROR_KEYS, f"error 键集不符: {sorted(err)}"
