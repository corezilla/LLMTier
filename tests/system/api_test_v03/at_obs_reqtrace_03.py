"""Case ID: OBS-REQTRACE-03

Endpoint: GET /v1/trace/{request_id}
Upstream Provider: 无（仅诊断读面；不触上游）
Model: 无
Auth: Bearer dev-data（data token，不应授权 admin 面）；对照 Bearer dev-admin

TS-002 依赖：
  Endpoint: http://192.168.1.9:8181（m5air 已部署实例）
  上游: 无（本 case 不触上游）
  模型: 无

TS-003：不触上游，无 provider endpoint。

目标：GET /v1/trace/{request_id} 以 data token 访问：HTTP 403 permission_denied，
无信息泄露（存在/未知 id 状态一致，授权先于存在性）。
"""
from __future__ import annotations

import pytest


@pytest.mark.api_a
def test_obs_reqtrace_03_data_token_403_no_leak(api_client, admin_client):
    unknown = api_client.get("/v1/trace/req_does_not_exist")
    assert unknown.status_code == 403, (
        f"data token 期望 403，实际 {unknown.status_code}: {unknown.text}"
    )
    err = unknown.json()["error"]
    assert set(err.keys()) == {"message", "type", "code", "param", "retryable"}, (
        f"错误信封键集不符: {sorted(err.keys())}"
    )
    assert err["code"] == "permission_denied", f"code 不符: {err}"
    assert err["type"] == "request_error", f"type 不符: {err}"
    assert err["retryable"] is False, f"retryable 应为 False: {err}"

    listing = admin_client.get("/v1/diagnostics/traces", params={"limit": 1})
    assert listing.status_code == 200, (
        f"traces 列表期望 200，实际 {listing.status_code}: {listing.text}"
    )
    items = listing.json()["items"]
    if items:
        real = api_client.get(f"/v1/trace/{items[0]['request_id']}")
        assert real.status_code == 403, (
            f"data token 对真实 id 期望 403，实际 {real.status_code}: {real.text}"
        )
        assert real.json()["error"]["code"] == "permission_denied", (
            f"真实 id code 不泄露存在性: {real.json()}"
        )

    admin_unknown = admin_client.get("/v1/trace/req_does_not_exist")
    assert admin_unknown.status_code == 404, (
        f"admin 对照未知 id 期望 404，实际 {admin_unknown.status_code}: {admin_unknown.text}"
    )
    assert admin_unknown.json()["error"]["code"] == "not_found", (
        f"admin 对照 code 应为 not_found: {admin_unknown.json()}"
    )

    alias = api_client.get("/tier/admin/v1/trace/req_does_not_exist")
    assert alias.status_code == 403, (
        f"别名 + data token 期望 403，实际 {alias.status_code}: {alias.text}"
    )
