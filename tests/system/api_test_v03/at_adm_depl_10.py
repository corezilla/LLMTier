"""Case ID: ST-depl-010

Endpoint: POST /v1/deployments
Upstream Provider: 无
Model: 无
Auth: Bearer dev-data (data token, 不应授权 admin)

目标：管理写面角色门——data 凭据访问 admin 写端点即 403。

断言：
- HTTP 403
- error 键集恰 5 键；code == "permission_denied"、type == "request_error"
- error.param is None、retryable is False
- 响应头含 X-Request-ID
- 零副作用：deployment 集合未变
"""
from __future__ import annotations

import pytest

ERROR_KEYS = {"message", "type", "code", "param", "retryable"}


@pytest.mark.api_a
def test_adm_depl_10_post_with_data_token(api_client, admin_client):
    before = admin_client.get("/v1/deployments")
    assert before.status_code == 200
    before_ids = {d["id"] for d in before.json()["data"]}

    body = {
        "id": "x",
        "name": "x",
        "provider_id": "provider_local",
        "backend_model": "m",
    }
    resp = api_client.post("/v1/deployments", json=body)
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

    after = admin_client.get("/v1/deployments")
    assert after.status_code == 200
    after_ids = {d["id"] for d in after.json()["data"]}
    assert after_ids == before_ids, f"被拒 POST 产生了副作用: {after_ids - before_ids}"
