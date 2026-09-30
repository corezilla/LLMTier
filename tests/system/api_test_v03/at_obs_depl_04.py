"""Case ID: OBS-DEPL-04

Endpoint: PATCH /v1/deployments/{deployment_id}/diagnostics
Upstream Provider: 无（写路径项校验；不触上游）
Model: 无
Auth: Bearer dev-admin

TS-002 依赖：
  Endpoint: 专用临时 LLMTier 实例（llmtier_b，独立临时 SQLite/端口）
  上游: prov_b 指向 LAN IP 上的 fake provider（TS-003，本 case 不触）
  模型: depl_b（backend_model=test-model）

TS-003：本 case 不触发推理，无 provider endpoint 请求。

目标：PATCH /v1/deployments/{id}/diagnostics 提交非法注入项：HTTP 400
invalid_injection（param 指向被拒字段），不写入任何注入行。

注（实现 vs case doc，见报告 discrepancy）：case doc §1 断言实现用
`bool(item.get("enabled"))` 接受任意 truthy；实测 `_validate` 已要求
`isinstance(enabled, bool)`，非 bool（含缺失）→ 400 invalid_injection param="enabled"
（`src/libdiag/injections.py:34-36`）。本脚本按实现断言该严格校验。
"""
from __future__ import annotations

import pytest

DIAG_PATH = "/v1/deployments/depl_b/diagnostics"
INVALID_ITEMS = [
    ({"type": "bogus", "config": {}, "enabled": True}, "type"),
    ({"type": "delay", "config": "x", "enabled": True}, "config"),
    ({"type": "fault_502", "config": {}, "enabled": True}, "error_body"),
    ({"type": "fault_502", "config": {"error_body": ""}, "enabled": True}, "error_body"),
    ({"type": "fault_502", "config": {"error_body": 123}, "enabled": True}, "error_body"),
    ({"type": "delay", "config": {"delay_ms": 60001}, "enabled": True}, "delay_ms"),
    ({"type": "delay", "config": {"delay_ms": -1}, "enabled": True}, "delay_ms"),
    ({"type": "delay", "config": {"delay_ms": "1000"}, "enabled": True}, "delay_ms"),
    ({"type": "delay", "config": {"delay_ms": True}, "enabled": True}, "delay_ms"),
    ({"type": "rate_limit", "config": {"retry_after_sec": 301}, "enabled": True}, "retry_after_sec"),
    ({"type": "stream_terminate", "config": {"stream_terminate_after_events": 0}, "enabled": True}, "stream_terminate_after_events"),
    ({"type": "malformed_event", "config": {"malformed_after_events": 10001, "malformed_event_type": "invalid_json"}, "enabled": True}, "malformed_after_events"),
    ({"type": "malformed_event", "config": {"malformed_after_events": 1, "malformed_event_type": "bogus"}, "enabled": True}, "malformed_event_type"),
]


def _assert_invalid(resp, param):
    assert resp.status_code == 400, (
        f"期望 400，实际 {resp.status_code}: {resp.text}"
    )
    err = resp.json()["error"]
    assert set(err.keys()) == {"message", "type", "code", "param", "retryable"}, (
        f"错误信封键集不符: {sorted(err.keys())}"
    )
    assert err["code"] == "invalid_injection", f"code 不符: {err}"
    assert err["type"] == "request_error", f"type 不符: {err}"
    assert err["retryable"] is False, f"retryable 应为 False: {err}"
    assert err["param"] == param, f"param 应指向 {param}: {err}"


@pytest.mark.api_b
def test_obs_depl_04_invalid_items_400_no_write(llmtier_b):
    client = llmtier_b.admin_client()
    client.patch(DIAG_PATH, json={"items": []})
    orig = client.get(DIAG_PATH)
    assert orig.status_code == 200 and orig.json() == [], f"初始注入应为空: {orig.text}"
    orig_raw = orig.content
    for item, param in INVALID_ITEMS:
        _assert_invalid(client.patch(DIAG_PATH, json={"items": [item]}), param)

    _assert_invalid(client.patch(DIAG_PATH, json={"items": "x"}), None)

    mixed = client.patch(
        DIAG_PATH,
        json={"items": [
            {"type": "delay", "config": {"delay_ms": 1000}, "enabled": True},
            {"type": "bogus", "config": {}, "enabled": True},
        ]},
    )
    assert mixed.status_code == 400, f"混合项期望 400，实际 {mixed.status_code}: {mixed.text}"
    after = client.get(DIAG_PATH)
    assert after.content == orig_raw, f"非法序列出现部分写入: {after.json()}"
    client.close()
