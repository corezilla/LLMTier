"""Case ID: ST-DEPL-011

Endpoint: PATCH /v1/deployments/dep_local_gemma
Upstream Provider: 无
Model: 无
Auth: Bearer dev-data (data token, 不应授权 admin)

目标：管理写面角色门——data 凭据访问 admin 写端点即 403。

断言：
- HTTP 403
- error 键集恰 5 键；code == "permission_denied"、type == "request_error"
- error.param is None、retryable is False
- 响应头含 X-Request-ID
- 零副作用：dep_local_gemma 的 version/ETag 不变
"""
from __future__ import annotations

import pytest

ERROR_KEYS = {"message", "type", "code", "param", "retryable"}


@pytest.mark.api_a
def test_adm_depl_11_patch_with_data_token(api_client, admin_client):
    before = admin_client.get("/v1/deployments/dep_local_gemma")
    assert before.status_code == 200
    before_version = before.json()["version"]
    before_etag = before.headers.get("ETag")

    resp = api_client.patch("/v1/deployments/dep_local_gemma", json={"name": "x"})
    assert resp.status_code == 403, f"期望 403，实际 {resp.status_code}: {resp.text}"
    assert resp.headers.get("X-Request-ID"), "缺 X-Request-ID 响应头"
    body_json = resp.json()
    assert set(body_json) == {"error"}, f"顶层键集不符: {set(body_json)}"
    err = body_json["error"]
    assert set(err) == ERROR_KEYS, f"error 键集不符（恰 5 键）: {set(err)}"
    assert err["code"] == "permission_denied", f"error.code != 'permission_denied': {err}"
    assert err["type"] == "request_error", f"error.type != 'request_error': {err}"
    assert err["param"] is None, f"error.param 应为 None: {err}"
    assert err["retryable"] is False, f"error.retryable != False: {err}"

    after = admin_client.get("/v1/deployments/dep_local_gemma")
    assert after.status_code == 200
    assert after.json()["version"] == before_version, "被拒 PATCH 改动了 baseline deployment"
    assert after.headers.get("ETag") == before_etag, "被拒 PATCH 改动了 baseline ETag"
