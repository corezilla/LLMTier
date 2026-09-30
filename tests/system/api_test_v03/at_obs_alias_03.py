"""Case ID: OBS-ALIAS-03

Endpoint: GET /tier/admin/v1/trace/{request_id} ≡ /v1/trace/{request_id}
Upstream Provider: 无（诊断读面；不触上游）
Model: 无
Auth: Bearer dev-admin

TS-002 依赖：
  Endpoint: http://192.168.1.9:8181（m5air 已部署实例）
  上游: 无（本 case 不触上游）
  模型: 无

TS-003：不触上游，无 provider endpoint。

目标：单请求 trace 别名与扁平路径由同一 handler 服务：status 与响应体逐字节等价
（含未知 id 的 404 信封）。无真实 trace 时以 404 等价完成判定。
"""
from __future__ import annotations

import pytest

FLAT = "/v1/trace/req_does_not_exist"
ALIAS = "/tier/admin/v1/trace/req_does_not_exist"


@pytest.mark.api_a
def test_obs_alias_03_trace_equivalence(admin_client):
    flat = admin_client.get(FLAT)
    alias = admin_client.get(ALIAS)
    assert flat.status_code == 404, f"未知 id 扁平路径期望 404，实际 {flat.status_code}: {flat.text}"
    assert alias.status_code == 404, f"未知 id 别名路径期望 404，实际 {alias.status_code}: {alias.text}"
    assert flat.content == alias.content, (
        f"404 body 非逐字节等价: {flat.json()} != {alias.json()}"
    )
    assert flat.json()["error"]["code"] == "not_found", f"code 不符: {flat.json()}"

    listing = admin_client.get("/v1/diagnostics/traces", params={"limit": 1})
    assert listing.status_code == 200, (
        f"traces 列表期望 200，实际 {listing.status_code}: {listing.text}"
    )
    items = listing.json()["items"]
    if items:
        rid = items[0]["request_id"]
        flat_ok = admin_client.get(f"/v1/trace/{rid}")
        alias_ok = admin_client.get(f"/tier/admin/v1/trace/{rid}")
        assert flat_ok.status_code == alias_ok.status_code == 200, (
            f"正向 status 不等价: flat={flat_ok.status_code} alias={alias_ok.status_code}"
        )
        assert flat_ok.content == alias_ok.content, (
            f"正向 body 非逐字节等价: {flat_ok.json()} != {alias_ok.json()}"
        )
