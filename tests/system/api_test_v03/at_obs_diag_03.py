"""Case ID: OBS-DIAG-03

Endpoint: PATCH /v1/diagnostics
Upstream Provider: 无（注入开关写面；不触上游）
Model: 无
Auth: Bearer dev-admin

TS-002 依赖：
  Endpoint: 专用临时 LLMTier 实例（llmtier_b，独立临时 SQLite/端口）
  上游: prov_b 指向 LAN IP 上的 fake provider（TS-003）
  模型: depl_b（backend_model=test-model）

TS-003：本 case 不触发推理，无 provider endpoint 请求。

目标：PATCH /v1/diagnostics 提交非布尔开关值：HTTP 400 invalid_request
（param 指向被拒键），开关状态不变、无部分写入。

注（实现 vs openapi，见报告 discrepancy）：handler 用 `_optional_boolean` 对显式
`null` 也判 400 invalid_request（param=key），与 openapi `boolean` 契约一致；
本条按实测断言 400。
"""
from __future__ import annotations

import pytest

INVALID_BODIES = [
    ({"snapshots_enabled": "yes"}, "snapshots_enabled"),
    ({"snapshots_enabled": 1}, "snapshots_enabled"),
    ({"snapshots_enabled": 0}, "snapshots_enabled"),
    ({"stats_enabled": "true"}, "stats_enabled"),
    ({"stats_enabled": 0}, "stats_enabled"),
    ({"snapshots_enabled": []}, "snapshots_enabled"),
    ({"stats_enabled": {}}, "stats_enabled"),
    ({"snapshots_enabled": None}, "snapshots_enabled"),
    ({"stats_enabled": None}, "stats_enabled"),
]


@pytest.mark.api_b
def test_obs_diag_03_invalid_switch_value_400_no_side_effect(llmtier_b):
    client = llmtier_b.admin_client()
    orig_raw = client.get("/v1/diagnostics").content
    for body, param in INVALID_BODIES:
        resp = client.patch("/v1/diagnostics", json=body)
        assert resp.status_code == 400, (
            f"{body} 期望 400，实际 {resp.status_code}: {resp.text}"
        )
        err = resp.json()["error"]
        assert set(err.keys()) == {"message", "type", "code", "param", "retryable"}, (
            f"错误信封键集不符: {sorted(err.keys())}"
        )
        assert err["code"] == "invalid_request", f"{body} code 不符: {err}"
        assert err["type"] == "request_error", f"{body} type 不符: {err}"
        assert err["retryable"] is False, f"{body} retryable 应为 False: {err}"
        assert err["param"] == param, f"{body} param 应指向 {param}: {err}"

        after = client.get("/v1/diagnostics")
        assert after.content == orig_raw, (
            f"{body} 产生了副作用（开关被改）: {after.json()}"
        )
    client.close()
