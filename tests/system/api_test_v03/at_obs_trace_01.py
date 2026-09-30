"""Case ID: OBS-TRACE-01

Endpoint: GET /v1/diagnostics/traces
Upstream Provider: 无（仅诊断读面；不触上游）
Model: 无
Auth: Bearer dev-admin

TS-002 依赖：
  Endpoint: http://192.168.1.9:8181（m5air 已部署实例）
  上游: 无（本 case 不触上游）
  模型: 无

TS-003：不触上游，无 provider endpoint。

目标：GET /v1/diagnostics/traces 按 request_id 去重列出请求 trace：TracePage
顶层键集恰 {items, next_cursor, has_more}，同一 request_id 至多出现一次，
每项为合法 TraceView（stages 有序且 ≥1）。空页合法。
"""
from __future__ import annotations

import pytest

TRACE_PATH = "/v1/diagnostics/traces"
PAGE_KEYS = {"items", "next_cursor", "has_more"}
VIEW_KEYS = {"request_id", "correlation_id", "stages", "snapshot", "usage"}
STAGE_KEYS = {"stage", "timestamp", "detail"}


@pytest.mark.api_a
def test_obs_trace_01_dedup_and_page_shape(admin_client):
    resp = admin_client.get(TRACE_PATH, params={"limit": 50})
    assert resp.status_code == 200, (
        f"期望 200，实际 {resp.status_code}: {resp.text}"
    )
    assert "application/json" in resp.headers.get("content-type", ""), (
        f"Content-Type 非 JSON: {resp.headers.get('content-type')}"
    )
    body = resp.json()
    assert set(body.keys()) == PAGE_KEYS, (
        f"TracePage 键集不符: {sorted(body.keys())}"
    )
    assert isinstance(body["items"], list), f"items 应为数组: {body['items']!r}"
    assert type(body["has_more"]) is bool, f"has_more 应为 JSON 布尔: {body['has_more']!r}"
    assert body["next_cursor"] is None or isinstance(body["next_cursor"], str), (
        f"next_cursor 应为字符串或 null: {body['next_cursor']!r}"
    )

    request_ids = [item["request_id"] for item in body["items"]]
    assert len(request_ids) == len(set(request_ids)), (
        f"request_id 未去重: {request_ids}"
    )

    for item in body["items"]:
        assert set(item.keys()) == VIEW_KEYS, (
            f"TraceView 键集不符: {sorted(item.keys())}"
        )
        assert isinstance(item["request_id"], str) and item["request_id"], (
            f"request_id 应为非空字符串: {item['request_id']!r}"
        )
        assert item["correlation_id"] is None or isinstance(item["correlation_id"], str), (
            f"correlation_id 应为字符串或 null: {item['correlation_id']!r}"
        )
        stages = item["stages"]
        assert isinstance(stages, list) and len(stages) >= 1, (
            f"stages 应 ≥1 项: {stages!r}"
        )
        timestamps = []
        for stage in stages:
            assert set(stage.keys()) == STAGE_KEYS, (
                f"TraceStage 键集不符: {sorted(stage.keys())}"
            )
            assert isinstance(stage["stage"], str) and len(stage["stage"]) <= 64, (
                f"stage 应为 ≤64 字符串: {stage['stage']!r}"
            )
            assert isinstance(stage["timestamp"], str), (
                f"timestamp 应为字符串: {stage['timestamp']!r}"
            )
            assert stage["detail"] is None or isinstance(stage["detail"], dict), (
                f"detail 应为对象或 null: {stage['detail']!r}"
            )
            timestamps.append(stage["timestamp"])
        assert timestamps == sorted(timestamps), (
            f"stages 未按 timestamp 升序: {timestamps}"
        )
        snapshot = item["snapshot"]
        if snapshot is not None:
            assert isinstance(snapshot, dict), f"snapshot 应为对象或 null: {snapshot!r}"
            assert len(snapshot) == 11, f"snapshot 应为 11 键 SnapshotView: {sorted(snapshot.keys())}"
        usage = item["usage"]
        if usage is not None:
            assert isinstance(usage, dict), f"usage 应为对象或 null: {usage!r}"
            assert len(usage) == 8, f"usage 应为 8 键 UsageView: {sorted(usage.keys())}"

    if body["has_more"] and body["next_cursor"]:
        nxt = admin_client.get(TRACE_PATH, params={"limit": 50, "cursor": body["next_cursor"]})
        assert nxt.status_code == 200, (
            f"下一页期望 200，实际 {nxt.status_code}: {nxt.text}"
        )
        nxt_ids = {item["request_id"] for item in nxt.json()["items"]}
        assert not (nxt_ids & set(request_ids)), (
            "跨页 request_id 重叠"
        )
