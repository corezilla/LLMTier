"""Case ID: ST-emb-009

Endpoint: POST /v1/embeddings
Upstream Provider: prov_b（LAN fake provider，backend_model 逐子测改写）
Model: Senior（指向 depl_b）
Auth: Bearer dev-data

TS-002 依赖：
  Endpoint: 临时 LLMTier 实例（llmtier_b_emb_contract），127.0.0.1:<临时端口>
  上游: LAN fake provider（fake_provider_b），backend_model in
        {force-bad-object, force-non-array-data, force-bad-vector, force-bad-base64}
  Auth: Bearer dev-data

目标：验证上游返回**各类**无法归一的 Embeddings 载荷 → 502 provider_contract_error。

实现（哪一层归一）：
- src/inference/providers/openai.py::embed — object != "list" / data 非数组 → 502
- src/inference/embeddings.py:57/60 — 非法 base64 / 非法向量 → 502

断言（四个子测各自独立）：
- HTTP 502；content-type application/json；错误信封（无成功 data）
- error 键集恰 5；code=="provider_contract_error"、type=="server_error"、
  param is None、retryable is False
"""
from __future__ import annotations

import pytest

ERROR_KEYS = {"message", "type", "code", "param", "retryable"}
# backend_model -> (请求 encoding_format, 说明)
CASES = [
    ("force-bad-object", "float", "object != 'list'"),
    ("force-non-array-data", "float", "data 非数组"),
    ("force-bad-vector", "float", "元素缺 embedding（非法向量）"),
    ("force-bad-base64", "base64", "非法 base64"),
]


def _set_backend_model(admin, backend_model: str) -> None:
    view = admin.get("/v1/deployments/depl_b")
    assert view.status_code == 200, f"GET deployment 失败: {view.text}"
    etag = view.headers.get("ETag")
    assert etag, "GET deployment 缺少 ETag"
    resp = admin.patch(
        "/v1/deployments/depl_b",
        json={"backend_model": backend_model},
        headers={"If-Match": etag},
    )
    assert resp.status_code == 200, f"PATCH backend_model 失败: {resp.status_code}: {resp.text}"


@pytest.mark.api_b
def test_dp_emb_09_upstream_contract_error_502(llmtier_b_emb_contract):
    admin = llmtier_b_emb_contract.admin_client()
    client = llmtier_b_emb_contract.api_client()
    try:
        for backend_model, encoding, label in CASES:
            _set_backend_model(admin, backend_model)
            resp = client.post(
                "/v1/embeddings",
                json={"model": "Senior", "input": "hello", "encoding_format": encoding},
            )
            assert resp.status_code == 502, (
                f"[{backend_model}/{label}] 期望 502，实际 {resp.status_code}: {resp.text}"
            )
            assert resp.headers.get("content-type", "").startswith("application/json"), (
                f"[{backend_model}] 契约错误应返回 JSON 信封"
            )
            body = resp.json()
            assert set(body) == {"error"}, f"[{backend_model}] 顶层键集不符: {sorted(body)}"
            assert "data" not in body, f"[{backend_model}] 契约违规载荷被当成功流出: {body}"
            err = body["error"]
            assert set(err) == ERROR_KEYS, f"[{backend_model}] error 键集不符: {sorted(err)}"
            assert err["code"] == "provider_contract_error", (
                f"[{backend_model}/{label}] error.code 不符: {err}"
            )
            assert err["type"] == "server_error", f"[{backend_model}] error.type 不符: {err}"
            assert err["param"] is None, f"[{backend_model}] error.param 非 null: {err}"
            assert err["retryable"] is False, f"[{backend_model}] error.retryable 非 False: {err}"
    finally:
        _set_backend_model(admin, "force-bad-contract")
        client.close()
        admin.close()
