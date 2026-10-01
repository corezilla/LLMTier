"""Case ID: ST-resp-022

Endpoint: POST /v1/responses；诊断注入 PATCH /v1/deployments/depl_b/diagnostics
Upstream Provider: 故障注入（fault_503，depl_b）
Model: Senior（指向 depl_b）
Auth: Bearer dev-data / dev-admin

TS-002 依赖：
  Endpoint: 临时 LLMTier 实例（llmtier_b_diag），127.0.0.1:<临时端口>
  上游: LAN fake provider（fake_provider_b）；fault_503 注入命中即抛错
  Auth: Bearer dev-data

目标：注入 fault_503 → 503 provider_unavailable（type server_error，retryable=true），
不按 SSE 解析。

实现：src/inference/responses.py:108-113
  kind == "fault_503" → ApiError(503, "provider_unavailable", fault_body, retryable=True)

断言：
- HTTP 503 + code "provider_unavailable"、type "server_error"
- retryable is True、param is None、message 含注入 error_body、键集恰 5 键
- teardown：PATCH {"items": []} 清空注入
"""
from __future__ import annotations

import pytest

ERROR_KEYS = {"message", "type", "code", "param", "retryable"}


@pytest.mark.api_b
def test_dp_resp_22_injected_503_provider_unavailable(llmtier_b_diag):
    admin = llmtier_b_diag.admin_client()
    endpoint = "/v1/deployments/depl_b/diagnostics"
    injection = {
        "items": [
            {
                "type": "fault_503",
                "config": {"error_body": "injected upstream unavailable"},
                "enabled": True,
            }
        ]
    }
    client = llmtier_b_diag.api_client()
    try:
        set_resp = admin.patch(endpoint, json=injection)
        assert set_resp.status_code == 200, (
            f"写入 fault_503 失败: {set_resp.status_code}: {set_resp.text}"
        )
        assert any(
            item.get("type") == "fault_503" and item.get("enabled")
            for item in set_resp.json()
        ), f"fault_503 未生效: {set_resp.json()}"

        resp = client.post(
            "/v1/responses",
            json={
                "model": "Senior",
                "input": [{"role": "user", "content": "Hello"}],
                "stream": True,
                "store": False,
            },
        )
        assert resp.status_code == 503, f"期望 503，实际 {resp.status_code}: {resp.text}"
        assert resp.headers.get("content-type", "").startswith("application/json")
        err = resp.json().get("error") or {}
        assert err.get("code") == "provider_unavailable", f"error.code 不符: {err}"
        assert err.get("type") == "server_error", f"error.type 不符: {err}"
        assert err.get("retryable") is True, f"error.retryable 非 True: {err}"
        assert err.get("param") is None, f"error.param 非 null: {err}"
        assert "injected upstream unavailable" in err.get("message", ""), (
            f"message 不含注入体: {err}"
        )
        assert set(err) == ERROR_KEYS, f"error 键集不符: {sorted(err)}"
    finally:
        clear = admin.patch(endpoint, json={"items": []})
        assert clear.status_code == 200, f"清空注入失败: {clear.status_code}: {clear.text}"
        remaining = admin.get(endpoint)
        assert remaining.status_code == 200
        assert all(not item.get("enabled") for item in remaining.json()), (
            f"注入未清空: {remaining.json()}"
        )
        client.close()
        admin.close()
