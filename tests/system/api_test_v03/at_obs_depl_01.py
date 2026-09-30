"""Case ID: OBS-DEPL-01

Endpoint: GET /v1/deployments/{deployment_id}/diagnostics
Upstream Provider: 无（注入配置读面；不触上游）
Model: 无
Auth: Bearer dev-admin

TS-002 依赖：
  Endpoint: http://192.168.1.9:8181（m5air 已部署实例）
  上游: 无（本 case 不触上游）
  模型: 无（读注入配置，不触发推理）

TS-003：不触上游，无 provider endpoint。

目标：GET /v1/deployments/{id}/diagnostics 返回该 deployment 的故障注入配置：
HTTP 200 + InjectionView[]（每项恰 6 键），顶层为裸数组。
"""
from __future__ import annotations

import pytest

DEPLOYMENT_ID = "dep_local_gemma"
TYPES = {"fault_502", "fault_503", "delay", "rate_limit", "stream_terminate", "malformed_event"}
ITEM_KEYS = {"id", "deployment_id", "type", "config", "enabled", "updated_at"}


@pytest.mark.api_a
def test_obs_depl_01_injections_shape(admin_client):
    path = f"/v1/deployments/{DEPLOYMENT_ID}/diagnostics"
    resp = admin_client.get(path)
    assert resp.status_code == 200, (
        f"期望 200，实际 {resp.status_code}: {resp.text}"
    )
    assert "application/json" in resp.headers.get("content-type", ""), (
        f"Content-Type 非 JSON: {resp.headers.get('content-type')}"
    )
    body = resp.json()
    assert isinstance(body, list), f"顶层应为裸数组 InjectionView[]: {body!r}"

    for item in body:
        assert set(item.keys()) == ITEM_KEYS, (
            f"InjectionView 键集应恰 6 键: {sorted(item.keys())}"
        )
        for key in ("id", "deployment_id", "updated_at"):
            assert isinstance(item[key], str), f"{key} 应为字符串: {item[key]!r}"
        assert item["type"] in TYPES, f"type 越枚举: {item['type']!r}"
        assert isinstance(item["config"], dict), f"config 应为对象: {item['config']!r}"
        assert type(item["enabled"]) is bool, f"enabled 应为 JSON 布尔: {item['enabled']!r}"
        assert item["deployment_id"] == DEPLOYMENT_ID, (
            f"返回了别的 deployment 的注入: {item['deployment_id']!r}"
        )
