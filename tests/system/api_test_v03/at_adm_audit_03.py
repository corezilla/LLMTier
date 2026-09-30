"""Case ID: ADM-AUDIT-03

Endpoint: GET /v1/audit
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

TS-002 依赖：
  Endpoint: http://192.168.1.9:8181（m5air 已部署实例）

目标（VRC-MGMT-003 / ERR-REQ-VALIDATION）：审计 `limit` 的整数参数校验。
`app.py::_int_param` 对无法 int() 的输入抛 400 invalid_request（admin 鉴权后、
handler 前，不触库、无副作用）；不得静默回退默认 50 或返回 200 空页。

断言：
- GET /v1/audit?limit=abc → 400
- error.code=="invalid_request"、type=="request_error"、param is None、retryable is False
- limit 值非整数不得静默回退
- 对照 GET /v1/audit?limit=1 → 200（400 来自参数值而非端点/鉴权）
"""
from __future__ import annotations

import pytest

ERROR_KEYS = {"message", "type", "code", "param", "retryable"}


@pytest.mark.api_a
def test_adm_audit_03_invalid_limit(admin_client):
    resp = admin_client.get("/v1/audit", params={"limit": "abc"})
    assert resp.status_code == 400, f"返回 {resp.status_code}（期望 400）: {resp.text}"
    body = resp.json()
    assert set(body) == {"error"}, f"顶层键集不符: {set(body)}"
    err = body["error"]
    assert set(err) == ERROR_KEYS, f"error 键集不符（恰 5 键）: {set(err)}"
    assert err["code"] == "invalid_request", f"code != invalid_request: {err}"
    assert err["type"] == "request_error", f"type != request_error: {err}"
    assert err["param"] is None, f"param != None（_int_param 未传 param）: {err}"
    assert err["retryable"] is False, f"retryable != False: {err}"

    boundary = admin_client.get("/v1/audit", params={"limit": ""})
    assert boundary.status_code == 200, (
        f"空 limit 视为缺省应 200，实际 {boundary.status_code}: {boundary.text}")

    control = admin_client.get("/v1/audit", params={"limit": 1})
    assert control.status_code == 200, (
        f"对照 limit=1 期望 200，实际 {control.status_code}: {control.text}")
