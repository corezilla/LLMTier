"""Case ID: ST-resp-019

Endpoint: POST /v1/responses；探测 POST /v1/probes
Upstream Provider: prov_b（endpoint 为不可达 LAN 地址 http://192.168.1.254:9/v1）
Model: Senior（指向 depl_b）
Auth: Bearer dev-data / dev-admin

TS-002 依赖：
  Endpoint: 临时 LLMTier 实例（llmtier_b_unhealthy），127.0.0.1:<临时端口>
  上游: 不可达 LAN endpoint（TS-003，192.168.1.254:9）
  Auth: Bearer dev-data

目标：候选存在但全部不健康 → 503 model_unavailable（retryable=true），无上游调用。

实现：src/inference/routing.py:84
  if not healthy: raise ApiError(503, "model_unavailable",
                                 "All configured backends are unhealthy", retryable=True)

断言：
- 探测 200 且 status == "unhealthy"
- 被测 HTTP 503 + code "model_unavailable" + type "server_error"
  + param null + retryable True + 键集恰 5 键
"""
from __future__ import annotations

import pytest

ERROR_KEYS = {"message", "type", "code", "param", "retryable"}


@pytest.mark.api_b
def test_dp_resp_19_all_candidates_unhealthy(llmtier_b_unhealthy):
    admin = llmtier_b_unhealthy.admin_client()
    api = llmtier_b_unhealthy.api_client()
    try:
        probe = admin.post(
            "/v1/probes",
            json={"deployment_id": "depl_b", "confirm_external_call": True},
        )
        assert probe.status_code == 200, f"探测失败: {probe.status_code}: {probe.text}"
        assert probe.json().get("status") == "unhealthy", (
            f"不可达 endpoint 应探测为 unhealthy: {probe.json()}"
        )

        resp = api.post(
            "/v1/responses",
            json={
                "model": "Senior",
                "input": [{"role": "user", "content": "hi"}],
                "stream": True,
                "store": False,
            },
        )
    finally:
        admin.close()
        api.close()

    assert resp.status_code == 503, f"期望 503，实际 {resp.status_code}: {resp.text}"
    assert resp.headers.get("content-type", "").startswith("application/json")
    err = resp.json().get("error") or {}
    assert err.get("code") == "model_unavailable", f"error.code 不符: {err}"
    assert err.get("type") == "server_error", f"error.type 不符: {err}"
    assert err.get("param") is None, f"error.param 非 null: {err}"
    assert err.get("retryable") is True, f"error.retryable 非 True: {err}"
    assert set(err) == ERROR_KEYS, f"error 键集不符: {sorted(err)}"
