"""Case ID: ST-EMB-010

Endpoint: POST /v1/embeddings
Upstream Provider: prov_b（LAN fake provider，backend_model 逐子测改写）
Model: Senior（指向 depl_b）
Auth: Bearer dev-data

TS-002 依赖：
  Endpoint: 临时 LLMTier 实例（llmtier_b_emb_503），127.0.0.1:<临时端口>
  上游: LAN fake provider（fake_provider_b）
        - force-503 : 任意 POST 返回 503（HTTP 5xx 分支）
        - force-drop: 关闭连接、不返回 HTTP 响应（传输失败 / URLError 分支）
  Auth: Bearer dev-data

目标：验证上游 5xx **与传输失败**（URLError/断连）→ 503 provider_unavailable。

实现：src/inference/providers/openai.py::_request
（HTTPError>=500 → 503；URLError/TimeoutError/JSONDecodeError → 503）

断言（两个子测各自独立）：
- HTTP 503；content-type application/json；错误信封（无成功 data）
- error 键集恰 5；code=="provider_unavailable"、type=="server_error"、
  param is None、retryable is True
"""
from __future__ import annotations

import pytest

ERROR_KEYS = {"message", "type", "code", "param", "retryable"}
CASES = [
    ("force-503", "HTTP 5xx"),
    ("force-drop", "传输失败/断连"),
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
def test_dp_emb_10_upstream_unavailable_503(llmtier_b_emb_503):
    admin = llmtier_b_emb_503.admin_client()
    client = llmtier_b_emb_503.api_client()
    try:
        for backend_model, label in CASES:
            _set_backend_model(admin, backend_model)
            resp = client.post("/v1/embeddings", json={"model": "Senior", "input": "hello"})
            assert resp.status_code == 503, (
                f"[{backend_model}/{label}] 期望 503，实际 {resp.status_code}: {resp.text}"
            )
            assert resp.headers.get("content-type", "").startswith("application/json"), (
                f"[{backend_model}] 上游不可用应返回 JSON 信封"
            )
            body = resp.json()
            assert set(body) == {"error"}, f"[{backend_model}] 顶层键集不符: {sorted(body)}"
            assert "data" not in body, f"[{backend_model}] 上游不可用却流出成功载荷: {body}"
            err = body["error"]
            assert set(err) == ERROR_KEYS, f"[{backend_model}] error 键集不符: {sorted(err)}"
            assert err["code"] == "provider_unavailable", (
                f"[{backend_model}/{label}] error.code 不符: {err}"
            )
            assert err["type"] == "server_error", f"[{backend_model}] error.type 不符: {err}"
            assert err["param"] is None, f"[{backend_model}] error.param 非 null: {err}"
            assert err["retryable"] is True, f"[{backend_model}] error.retryable 非 True: {err}"
    finally:
        _set_backend_model(admin, "force-503")
        client.close()
        admin.close()
