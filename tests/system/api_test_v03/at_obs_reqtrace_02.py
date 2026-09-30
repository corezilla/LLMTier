"""Case ID: OBS-REQTRACE-02

Endpoint: GET /v1/trace/{request_id}
Upstream Provider: 无（仅诊断读面；不触上游）
Model: 无
Auth: Bearer dev-admin

TS-002 依赖：
  Endpoint: http://192.168.1.9:8181（m5air 已部署实例）
  上游: 无（本 case 不触上游）
  模型: 无

TS-003：不触上游，无 provider endpoint。

目标：GET /v1/trace/{request_id} 查询不存在的 request_id：HTTP 404 not_found，
不返回空 TraceView 的 200。
"""
from __future__ import annotations

import uuid

import pytest


@pytest.mark.api_a
def test_obs_reqtrace_02_unknown_id_404(admin_client):
    unknown_ids = [
        f"req_does_not_exist_{uuid.uuid4().hex}",
        "req_deadbeef0000000000000000000000",
        "x",
    ]
    for rid in unknown_ids:
        resp = admin_client.get(f"/v1/trace/{rid}")
        assert resp.status_code == 404, (
            f"id={rid!r} 期望 404，实际 {resp.status_code}: {resp.text}"
        )
        err = resp.json()["error"]
        assert set(err.keys()) == {"message", "type", "code", "param", "retryable"}, (
            f"错误信封键集不符: {sorted(err.keys())}"
        )
        assert err["code"] == "not_found", f"id={rid!r} code 不符: {err}"
        assert err["type"] == "request_error", f"id={rid!r} type 不符: {err}"
        assert err["retryable"] is False, f"id={rid!r} retryable 应为 False: {err}"

    control = admin_client.get("/v1/diagnostics/traces", params={"limit": 1})
    assert control.status_code == 200, (
        f"对照 traces 期望 200，实际 {control.status_code}: {control.text}"
    )
    items = control.json()["items"]
    if items:
        real = items[0]["request_id"]
        real_resp = admin_client.get(f"/v1/trace/{real}")
        assert real_resp.status_code == 200, (
            f"真实 id 对照期望 200，实际 {real_resp.status_code}: {real_resp.text}"
        )
