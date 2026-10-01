"""Case ID: ST-runtime-002

Endpoint: GET /v1/runtime
Upstream Provider: 无
Model: 无
Auth: Bearer dev-data（显式有效凭据）
      正向对照: Bearer dev-admin

TS-002 依赖：
  Endpoint: http://192.168.1.9:8181（m5air 已部署实例）

目标（VRC-INF-004 / ERR-AUTH-DENIED）：管理端点对"已认证但角色不足"的拒绝。
必须用**显式且有效的 data bearer**（Bearer dev-data）；不得用缺 Authorization 头
（受信 LAN/loopback 的无头请求会被授予共享 admin 主体，得到 200 而非 403）。

断言：
- 正向对照 admin_client GET /v1/runtime == 200
- api_client（Bearer dev-data）GET /v1/runtime == 403
- 顶层键集恰 {"error"}；error 恰 5 键；code=="permission_denied"、
  type=="request_error"、param is None、retryable is False
- body 为错误信封，不含 deployments/providers/queues 快照字段
"""
from __future__ import annotations

import pytest

from tests.system.api_test_v03.conftest import error_envelope

SNAPSHOT_FIELDS = {"deployments", "providers", "queues"}


@pytest.mark.api_a
def test_adm_runtime_02_data_credential_forbidden(api_client, admin_client):
    positive = admin_client.get("/v1/runtime")
    assert positive.status_code == 200, (
        f"admin 正向对照期望 200，实际 {positive.status_code}: {positive.text}")

    resp = api_client.get("/v1/runtime")
    assert resp.status_code == 403, (
        f"data 凭据期望 403，实际 {resp.status_code}: {resp.text}")
    body = resp.json()
    assert set(body) == {"error"}, f"顶层键集不符（应为错误信封）: {set(body)}"
    err = error_envelope(resp)
    assert err["code"] == "permission_denied", f"code != permission_denied: {err}"
    assert err["type"] == "request_error", f"type != request_error: {err}"
    assert err["param"] is None, f"param != None: {err}"
    assert err["retryable"] is False, f"retryable != False: {err}"

    leaked = SNAPSHOT_FIELDS & set(body)
    assert not leaked, f"403 响应泄露 runtime 快照字段: {leaked}"
