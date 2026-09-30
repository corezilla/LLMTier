"""Case ID: DP-EMB-09

Endpoint: POST /v1/embeddings
Upstream Provider: prov_b（LAN fake provider，backend_model="force-bad-contract"）
Model: Senior（指向 depl_b）
Auth: Bearer dev-data

TS-002 依赖：
  Endpoint: 临时 LLMTier 实例（llmtier_b_emb_contract），127.0.0.1:<临时端口>
  上游: LAN fake provider（fake_provider_b），对 /v1/embeddings 返回契约违规载荷
  Auth: Bearer dev-data

目标：验证上游返回无法归一的 Embeddings 载荷 → 502 provider_contract_error。

断言：
- HTTP 502
- error.code == "provider_contract_error"、type == "server_error"
- param is None、retryable is False、键集恰 5 键
- 无成功 data 载荷

实现：src/inference/providers/openai.py::embed（object != "list" → 502）。
"""
from __future__ import annotations

import pytest

ERROR_KEYS = {"message", "type", "code", "param", "retryable"}


@pytest.mark.api_b
def test_dp_emb_09_upstream_contract_error_502(llmtier_b_emb_contract):
    client = llmtier_b_emb_contract.api_client()
    try:
        resp = client.post("/v1/embeddings", json={"model": "Senior", "input": "hello"})
    finally:
        client.close()

    assert resp.status_code == 502, f"期望 502，实际 {resp.status_code}: {resp.text}"
    assert resp.headers.get("content-type", "").startswith("application/json")
    body = resp.json()
    assert "data" not in body, f"契约违规载荷被当成功流出: {body}"
    err = body.get("error") or {}
    assert err.get("code") == "provider_contract_error", f"error.code 不符: {err}"
    assert err.get("type") == "server_error", f"error.type 不符: {err}"
    assert err.get("param") is None, f"error.param 非 null: {err}"
    assert err.get("retryable") is False, f"error.retryable 非 False: {err}"
    assert set(err) == ERROR_KEYS, f"error 键集不符: {sorted(err)}"
