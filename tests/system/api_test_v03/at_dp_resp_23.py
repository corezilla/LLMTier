"""Case ID: DP-RESP-23

Endpoint: POST /v1/responses
Upstream Provider: prov_b（endpoint 为专属 LAN fake provider，按 model 返回预置 HTTP 码）
Model: Senior（指向 depl_b，backend_model 逐子测改写）
Auth: Bearer dev-data / dev-admin

TS-002 依赖：
  Endpoint: 临时 LLMTier 实例（llmtier_b_http_stub），127.0.0.1:<临时端口>
  上游: LAN fake provider（fake_provider_b），backend_model in
        {force-http-422, force-http-429, force-http-500} → /v1/responses 返回对应 HTTP
  Auth: Bearer dev-data

目标：真实上游非成功 HTTP → 沿用非 5xx 状态并归一 provider_error
（retryable 仅 {408,429}）；5xx 归一 503 provider_unavailable。

实现：src/inference/providers/openai.py:115-119
  >=500 → ApiError(503, "provider_unavailable", retryable=True)
  else   → ApiError(exc.code, "provider_error", retryable=exc.code in {408,429})

断言：
- 422：HTTP 422 + code "provider_error" + type "request_error" + param null
  + retryable False + 键集恰 5 键
- 429：HTTP 429 + code "provider_error" + retryable True
- 503（对照）：HTTP 503 + code "provider_unavailable" + retryable True

注：方案标题写"上游 4xx/5xx → provider_error"，实现 `openai.py` 对 5xx 返回
`provider_unavailable`（以代码为准）。
"""
from __future__ import annotations

import pytest

ERROR_KEYS = {"message", "type", "code", "param", "retryable"}


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
    assert resp.json().get("backend_model") == backend_model


def _post_responses(client):
    return client.post(
        "/v1/responses",
        json={
            "model": "Senior",
            "input": [{"role": "user", "content": "hi"}],
            "stream": True,
            "store": False,
        },
    )


@pytest.mark.api_b
def test_dp_resp_23_upstream_non_success_http(llmtier_b_http_stub):
    admin = llmtier_b_http_stub.admin_client()
    client = llmtier_b_http_stub.api_client()
    try:
        _set_backend_model(admin, "force-http-422")
        resp = _post_responses(client)
        assert resp.status_code == 422, f"4xx 应沿用原状态，实际 {resp.status_code}: {resp.text}"
        assert resp.headers.get("content-type", "").startswith("application/json")
        err = resp.json().get("error") or {}
        assert err.get("code") == "provider_error", f"error.code 不符: {err}"
        assert err.get("type") == "request_error", f"error.type 不符: {err}"
        assert err.get("param") is None, f"error.param 非 null: {err}"
        assert err.get("retryable") is False, f"422 的 retryable 应为 False: {err}"
        assert set(err) == ERROR_KEYS, f"error 键集不符: {sorted(err)}"

        _set_backend_model(admin, "force-http-429")
        resp = _post_responses(client)
        assert resp.status_code == 429, f"429 应沿用原状态，实际 {resp.status_code}: {resp.text}"
        err = resp.json().get("error") or {}
        assert err.get("code") == "provider_error", f"error.code 不符: {err}"
        assert err.get("retryable") is True, f"429 的 retryable 应为 True: {err}"

        _set_backend_model(admin, "force-http-500")
        resp = _post_responses(client)
        assert resp.status_code == 503, (
            f"真实上游 5xx 应归一 503，实际 {resp.status_code}: {resp.text}"
        )
        err = resp.json().get("error") or {}
        assert err.get("code") == "provider_unavailable", f"error.code 不符: {err}"
        assert err.get("type") == "server_error", f"error.type 不符: {err}"
        assert err.get("retryable") is True, f"5xx 的 retryable 应为 True: {err}"
        assert set(err) == ERROR_KEYS, f"error 键集不符: {sorted(err)}"
    finally:
        _set_backend_model(admin, "force-http-422")
        client.close()
        admin.close()
