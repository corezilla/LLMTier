"""Case ID: ST-sl-008

Endpoint: PATCH /v1/service-levels/{id}（非数组 deployment_ids）
Upstream Provider: provider_endpoint_b（LAN fake provider，TS-003）
Model: 无
Auth: Bearer dev-admin

TS-002 依赖：
  Endpoint: 临时 LLMTier 实例（llmtier_b，独立临时 SQLite/端口）
  上游: provider_endpoint_b（LAN fake provider，TS-003）
  fixture: admin_client_b；初始状态 Worker 存在

目标（VRC-MGMT-002 / ERR-REQ-VALIDATION）：Service Level PATCH 对
`deployment_ids` 类型的输入校验契约。

【实现 vs 设计偏差（已登记）】
设计文档 adm-sl-08.md 假设 `registry._capability_intersection` 不做类型校验，
非数组 `deployment_ids` 会抛 TypeError → 500 internal_error。但当前实现
`registry.py:300` 已在迭代前显式校验：
    require(isinstance(deployment_ids, list) and all(isinstance(rid, str) ...),
            400, "invalid_request", "deployment_ids must be an array of strings")
即非数组输入已是 400 invalid_request（设计期望的正确行为），500 路径不再存在。
按 adm-sl-08.md §5 的 FAIL 条款（"如实现修复后返回 400——则须更新本 case 与
§3.2/§11.1 后再判"），本脚本以**当前 code 行为**为 Oracle：断言 400 invalid_request。

断言：
- 前置 GET /v1/service-levels/Worker 200，取真实 ETag/version
- PATCH {"deployment_ids": 1} + If-Match → 400
- error.code=="invalid_request"、type=="request_error"、param=="deployment_ids"
- 零副作用：GET 后 Worker.version 不变
"""
from __future__ import annotations

import pytest


@pytest.mark.api_b
def test_adm_sl_08_non_array_deployment_ids(admin_client_b):
    get_resp = admin_client_b.get("/v1/service-levels/Worker")
    assert get_resp.status_code == 200, (
        f"Worker 详情期望 200，实际 {get_resp.status_code}: {get_resp.text}")
    tier = get_resp.json()
    etag = get_resp.headers.get("ETag")
    version_before = tier["version"]

    resp = admin_client_b.patch(
        "/v1/service-levels/Worker",
        json={"deployment_ids": 1},
        headers={"If-Match": etag},
    )
    assert resp.status_code == 400, (
        f"非数组 deployment_ids 期望 400（代码已含类型守卫），实际 {resp.status_code}: {resp.text}")
    body = resp.json()
    assert set(body) == {"error"}, f"顶层键集不符（应为错误信封）: {set(body)}"
    err = body["error"]
    assert set(err) == {"message", "type", "code", "param", "retryable"}, (
        f"error 键集不符（恰 5 键）: {set(err)}")
    assert err["code"] == "invalid_request", f"code != invalid_request: {err}"
    assert err["type"] == "request_error", f"type != request_error: {err}"
    assert err["param"] == "deployment_ids", f"param != deployment_ids: {err}"
    assert err["retryable"] is False, f"retryable != False: {err}"

    # Zero side-effect: the rejected PATCH must not bump the version.
    after = admin_client_b.get("/v1/service-levels/Worker")
    assert after.status_code == 200
    assert after.json()["version"] == version_before, (
        f"被拒 PATCH 产生了副作用: version {version_before} -> {after.json()['version']}")
