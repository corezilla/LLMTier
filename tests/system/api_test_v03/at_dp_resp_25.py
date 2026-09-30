"""Case ID: DP-RESP-25

Endpoint: POST /v1/responses
Upstream Provider: prov_b（endpoint 为专属 LAN fake provider，按 model 返回契约违规响应）
Model: Senior（指向 depl_b，backend_model 逐子测改写）
Auth: Bearer dev-data / dev-admin

TS-002 依赖：
  Endpoint: 临时 LLMTier 实例（llmtier_b_contract_stub），127.0.0.1:<临时端口>
  上游: LAN fake provider（fake_provider_b），backend_model in
        {force-non-sse, force-two-terminals, force-no-terminal, force-status-mismatch}
  Auth: Bearer dev-data

目标：上游响应无法归一为合法 terminal → 502 provider_contract_error，绝不流出成功。

实现：src/inference/providers/openai.py:90-105
  非 text/event-stream / 多个 terminal / 无合法 terminal / status 与类型不一致
  → ApiError(502, "provider_contract_error", ...)

断言（四个子测各自独立）：
- HTTP 502 + code "provider_contract_error" + type "server_error"
- param null + retryable False + 键集恰 5 键
- message 与违规对应
"""
from __future__ import annotations

import pytest

ERROR_KEYS = {"message", "type", "code", "param", "retryable"}
CASES = {
    "force-non-sse": ("did not return Responses SSE", "SSE"),
    "force-two-terminals": ("more than one terminal", "terminal"),
    "force-no-terminal": ("no valid terminal", "terminal"),
    "force-status-mismatch": ("disagree", "status"),
}


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
def test_dp_resp_25_upstream_contract_error(llmtier_b_contract_stub):
    admin = llmtier_b_contract_stub.admin_client()
    client = llmtier_b_contract_stub.api_client()
    try:
        for backend_model, (needle, label) in CASES.items():
            _set_backend_model(admin, backend_model)
            resp = client.post(
                "/v1/responses",
                json={
                    "model": "Senior",
                    "input": [{"role": "user", "content": "hi"}],
                    "stream": True,
                    "store": False,
                },
            )
            assert resp.status_code == 502, (
                f"[{backend_model}] 期望 502，实际 {resp.status_code}: {resp.text}"
            )
            assert resp.headers.get("content-type", "").startswith("application/json"), (
                f"[{backend_model}] 契约错误应返回 JSON 信封"
            )
            err = resp.json().get("error") or {}
            assert err.get("code") == "provider_contract_error", (
                f"[{backend_model}] error.code 不符: {err}"
            )
            assert err.get("type") == "server_error", f"[{backend_model}] error.type 不符: {err}"
            assert err.get("param") is None, f"[{backend_model}] error.param 非 null: {err}"
            assert err.get("retryable") is False, f"[{backend_model}] error.retryable 非 False: {err}"
            assert set(err) == ERROR_KEYS, f"[{backend_model}] error 键集不符: {sorted(err)}"
            assert needle in err.get("message", ""), (
                f"[{backend_model}] message 未体现违规（{label}）: {err.get('message')}"
            )
    finally:
        _set_backend_model(admin, "test-model")
        client.close()
        admin.close()
