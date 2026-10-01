"""Case ID: ST-pusage-004

Endpoint: GET /v1/providers/{id}/usage (不存在)
Upstream Provider: 无
Model: 无
Auth: Bearer dev-admin

TS-002 依赖：
  Endpoint: http://192.168.1.9:8181（m5air 已部署实例）
  被测 id: provider_does_not_exist_xyz（保证不存在）

目标（VRC-MGMT-006 / ERR-NOTFOUND）：未知 provider 的账号用量快照读取——
HTTP 404 + error.code=="not_found"，统一 5 键错误信封；不得退化为合成/空快照 200。

断言：
- HTTP 404
- error 键集恰为 {message,type,code,param,retryable}
- code=="not_found"、type=="request_error"、param is None、retryable is False
- 交叉核对：GET /v1/providers/provider_does_not_exist_xyz 同为 404 not_found
"""
from __future__ import annotations

import pytest

ERROR_KEYS = {"message", "type", "code", "param", "retryable"}


@pytest.mark.api_a
def test_adm_prov_usage_04_unknown_provider(admin_client):
    resp = admin_client.get("/v1/providers/provider_does_not_exist_xyz/usage")
    assert resp.status_code == 404, f"返回 {resp.status_code}（期望 404）: {resp.text}"
    body = resp.json()
    assert set(body) == {"error"}, f"顶层键集不符: {set(body)}"
    err = body["error"]
    assert set(err) == ERROR_KEYS, f"error 键集不符（恰 5 键）: {set(err)}"
    assert err["code"] == "not_found", f"code != not_found: {err}"
    assert err["type"] == "request_error", f"type != request_error: {err}"
    assert err["param"] is None, f"param != None: {err}"
    assert err["retryable"] is False, f"retryable != False: {err}"

    detail = admin_client.get("/v1/providers/provider_does_not_exist_xyz")
    assert detail.status_code == 404, (
        f"provider 详情期望 404，实际 {detail.status_code}: {detail.text}")
    assert detail.json()["error"]["code"] == "not_found"
