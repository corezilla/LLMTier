"""Case ID: ST-PROBE-003

Endpoint: POST /v1/probes (未知 deployment)
Upstream Provider: 无（资源解析前 404）
Model: 无
Auth: Bearer dev-admin

TS-002 依赖：
  Endpoint: 临时 LLMTier 实例（llmtier_b，独立临时 SQLite/端口）
  上游: provider_endpoint_b（LAN fake provider，TS-003）
  模型: 无（负向，不触上游）
  fixture: admin_client_b

目标（VRC-DIAG-004 / ERR-NOTFOUND）：探测对不存在 deployment 的资源解析。
确认门（confirm_external_call=true）通过后，registry.get_deployment 对未知 id
抛 404 not_found；不触上游、不写 probe_results、不改 health。

断言：
- 前置：GET /v1/deployments/does_not_exist == 404（确认 id 不存在）
- POST /v1/probes {deployment_id: "does_not_exist", confirm_external_call: true} == 404
- error 信封恰 5 键；code=="not_found"、type=="request_error"、param is None、retryable is False
- 零副作用：GET /v1/deployments 列表未变，且已知 deployment 的 health 未变
"""
from __future__ import annotations

import pytest

from tests.system.conftest import error_envelope


@pytest.mark.api_b
def test_adm_probe_03_unknown_deployment(admin_client_b):
    missing = admin_client_b.get("/v1/deployments/does_not_exist")
    assert missing.status_code == 404, (
        f"负向前置：does_not_exist 期望 404，实际 {missing.status_code}: {missing.text}")

    before = admin_client_b.get("/v1/deployments")
    assert before.status_code == 200, f"deployments 列表失败: {before.text}"
    before_items = {d["id"]: d.get("health") for d in before.json().get("data", [])}

    resp = admin_client_b.post(
        "/v1/probes",
        json={"deployment_id": "does_not_exist", "confirm_external_call": True},
    )
    assert resp.status_code == 404, (
        f"返回 {resp.status_code}（期望 404）: {resp.text}")
    err = error_envelope(resp)
    assert err["code"] == "not_found", f"code != not_found: {err}"
    assert err["type"] == "request_error", f"type != request_error: {err}"
    assert err["param"] is None, f"param != None: {err}"
    assert err["retryable"] is False, f"retryable != False: {err}"

    after = admin_client_b.get("/v1/deployments")
    assert after.status_code == 200
    after_items = {d["id"]: d.get("health") for d in after.json().get("data", [])}
    assert set(after_items) == set(before_items), (
        f"探测失败产生了资源副作用: {set(before_items)} -> {set(after_items)}")
    assert after_items == before_items, (
        f"探测失败改动了 health 等字段: {before_items} -> {after_items}")
