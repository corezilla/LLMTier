"""Case ID: ST-PROBE-002

Endpoint: POST /v1/probes (带 confirm + deployment_id)
Upstream Provider: 取决于 deployment
Model: 取决于 deployment
Auth: Bearer dev-admin

断言（doc §4/§5 主断言）：
- HTTP 200
- body 键集**恰为** {deployment_id,status,checked_at,may_have_incurred_cost}
  （`ProbeResult.additionalProperties:false`）
- deployment_id == 请求值；status ∈ {healthy,degraded,unhealthy}
- checked_at 为 RFC3339 字符串；may_have_incurred_cost 为 bool
- **health 落地核验**：GET /v1/deployments/<id>.health == body.status
  （证明 apply_probe_result 写库，与"仅返回 status"区分）

注：probe body 必须恰好是 {deployment_id, confirm_external_call}（admin.py:106）。
本 case 会真实调上游探测并写 probe_results/deployments.health 与审计
（观测型一次性写，设计已声明允许）。
"""
from __future__ import annotations

import re

import pytest

PROBE_RESULT_KEYS = {"deployment_id", "status", "checked_at", "may_have_incurred_cost"}
STATUS_ENUM = {"healthy", "degraded", "unhealthy"}
_RFC3339 = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
)


@pytest.mark.api_a
def test_adm_probe_02_with_confirm(admin_client):
    deployment_id = "dep_local_gemma"

    before = admin_client.get(f"/v1/deployments/{deployment_id}")
    assert before.status_code == 200, f"前置 GET deployment 失败: {before.text}"

    resp = admin_client.post(
        "/v1/probes",
        json={"deployment_id": deployment_id, "confirm_external_call": True},
    )
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()

    assert set(body) == PROBE_RESULT_KEYS, (
        f"ProbeResult 键集不符（应恰为 4 键）: {set(body)} != {PROBE_RESULT_KEYS}")
    assert body["deployment_id"] == deployment_id, f"deployment_id 回显错: {body}"
    assert body["status"] in STATUS_ENUM, f"status 非法: {body['status']}"
    assert isinstance(body["checked_at"], str) and _RFC3339.match(body["checked_at"]), (
        f"checked_at 非 RFC3339 字符串: {body['checked_at']!r}")
    assert isinstance(body["may_have_incurred_cost"], bool), (
        f"may_have_incurred_cost 非 bool: {body['may_have_incurred_cost']!r}")

    # health 落地核验——响应 status 必须等于 GET deployment 的 health。
    after = admin_client.get(f"/v1/deployments/{deployment_id}")
    assert after.status_code == 200, f"health 落地核验 GET deployment 失败: {after.text}"
    deployed_health = after.json().get("health")
    assert deployed_health == body["status"], (
        f"health 未落地：响应 status={body['status']} 但 deployment.health={deployed_health}")
