"""Case ID: ADM-SL-11

Endpoint: DELETE /v1/service-levels/Senior
Upstream Provider: 无
Model: 无
Auth: Bearer dev-data (data token, 不应授权 admin)

目标：管理写面角色门——data 凭据访问 admin 写端点即 403（拒绝先于资源变更，零副作用）。

断言：
- HTTP 403
- error 键集恰 5 键；code == "permission_denied"、type == "request_error"
- error.param is None、retryable is False
- 响应头含 X-Request-ID
- 零副作用：Senior 仍存在
"""
from __future__ import annotations

import pytest

ERROR_KEYS = {"message", "type", "code", "param", "retryable"}


@pytest.mark.api_a
def test_adm_sl_11_delete_with_data_token(api_client, admin_client):
    resp = api_client.request("DELETE", "/v1/service-levels/Senior", content=b"{}")
    assert resp.status_code == 403, f"期望 403，实际 {resp.status_code}: {resp.text}"
    assert resp.headers.get("X-Request-ID"), "缺 X-Request-ID 响应头"
    body = resp.json()
    assert set(body) == {"error"}, f"顶层键集不符: {set(body)}"
    err = body["error"]
    assert set(err) == ERROR_KEYS, f"error 键集不符（恰 5 键）: {set(err)}"
    assert err["code"] == "permission_denied", f"error.code != 'permission_denied': {err}"
    assert err["type"] == "request_error", f"error.type != 'request_error': {err}"
    assert err["param"] is None, f"error.param 应为 None: {err}"
    assert err["retryable"] is False, f"error.retryable != False: {err}"

    after = admin_client.get("/v1/service-levels/Senior")
    assert after.status_code == 200, "被拒 DELETE 不应删除 Senior"
