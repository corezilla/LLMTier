"""Case ID: DP-RESP-11

Endpoint: POST /v1/responses
Upstream Provider: 故障注入（fault_502，depl_b）
Model: Senior（指向 depl_b）
Auth: Bearer dev-data

目标：验证上游 provider 返回 502 时 LLMTier 的错误传播行为。

实现（design：走真实注入 API，不再 monkeypatch prov_b.endpoint）：
- B-class：PATCH /v1/deployments/depl_b/diagnostics 写入 fault_502
- 注入命中后 POST /v1/responses（stream=true）→ 502 provider_failure
- teardown 必须 items:[] 清空注入，绝不残留 prov_b.endpoint 指向死端口

断言：
- HTTP 502
- error.code == "provider_failure"、type == "server_error"、param is None
- error.retryable is True
- error.message 含注入的 error_body
- 注入命中 trace 证据：GET /v1/trace/{X-Request-ID} 的 usage.source == "injected"
"""
from __future__ import annotations

import httpx
import pytest


def _assert_injected_trace(admin_client, request_id: str) -> None:
    trace = admin_client.get(f"/v1/trace/{request_id}")
    assert trace.status_code == 200, f"trace 查询失败: {trace.status_code}: {trace.text}"
    usage = trace.json().get("usage") or {}
    assert usage.get("source") == "injected", (
        f"trace usage.source 应为 'injected'（注入命中证据）: {usage}"
    )


@pytest.mark.api_b
def test_dp_resp_11_upstream_502_provider_failure(admin_client_b, llmtier_b):
    deployment_id = "depl_b"
    endpoint = f"/v1/deployments/{deployment_id}/diagnostics"
    injection = {
        "items": [
            {
                "type": "fault_502",
                "config": {"error_body": "injected upstream failure"},
                "enabled": True,
            }
        ]
    }
    try:
        set_resp = admin_client_b.patch(endpoint, json=injection)
        assert set_resp.status_code == 200, (
            f"写入 fault_502 失败: {set_resp.status_code}: {set_resp.text}"
        )
        configured = set_resp.json()
        assert any(
            item.get("type") == "fault_502" and item.get("enabled")
            for item in configured
        ), f"fault_502 未生效: {configured}"

        with httpx.Client(
            base_url=llmtier_b.base_url,
            headers={"Authorization": "Bearer dev-data"},
            timeout=httpx.Timeout(30.0, connect=5.0),
        ) as api_client:
            resp = api_client.post(
                "/v1/responses",
                json={
                    "model": "Senior",
                    "input": [{"role": "user", "content": "Hello"}],
                    "stream": True,
                    "store": False,
                },
            )
        assert resp.status_code == 502, f"期望 502，实际 {resp.status_code}: {resp.text}"
        err = resp.json().get("error") or {}
        assert err.get("code") == "provider_failure", f"error.code != 'provider_failure': {err}"
        assert err.get("type") == "server_error", f"error.type != 'server_error': {err}"
        assert err.get("param") is None, f"error.param 非 null: {err}"
        assert err.get("retryable") is True, f"error.retryable != True: {err}"
        assert "injected upstream failure" in err.get("message", ""), f"message 不符: {err}"

        request_id = resp.headers.get("X-Request-ID")
        assert request_id, f"响应缺 X-Request-ID: {dict(resp.headers)}"
        _assert_injected_trace(admin_client_b, request_id)
    finally:
        clear = admin_client_b.patch(endpoint, json={"items": []})
        assert clear.status_code == 200, f"清空注入失败: {clear.status_code}: {clear.text}"
        remaining = admin_client_b.get(endpoint)
        assert remaining.status_code == 200
        assert all(not item.get("enabled") for item in remaining.json()), (
            f"注入未清空: {remaining.json()}"
        )
