"""Case ID: OBS-SNAP-01

Endpoint: GET /v1/diagnostics/snapshots
Upstream Provider: 无（仅诊断读面；不触上游）
Model: 无
Auth: Bearer dev-admin

TS-002 依赖：
  Endpoint: http://192.168.1.9:8181（m5air 已部署实例）
  上游: 无（本 case 不触上游）
  模型: 无

TS-003：不触上游，无 provider endpoint。

目标：GET /v1/diagnostics/snapshots 返回 SnapshotPage：顶层键集恰
{items, next_cursor, has_more}，每项为恰好 11 键的 SnapshotView，且内容已脱敏
（upstream_url 去 query、error_summary ≤256B、不含 Secret/凭据/正文）。
"""
from __future__ import annotations

import re

import pytest

SNAP_KEYS = {
    "id", "request_id", "captured_at", "upstream_url", "backend_model",
    "http_status", "latency_ms", "error_summary", "model", "deployment_id",
    "snapshot_type",
}
SNAPSHOT_TYPES = {"upstream", "error"}
SECRET_LITERALS = ("9832", "Authorization", "Bearer ", "secret_ref")


@pytest.mark.api_a
def test_obs_snap_01_page_shape_and_redaction(admin_client):
    resp = admin_client.get("/v1/diagnostics/snapshots", params={"limit": 50})
    assert resp.status_code == 200, (
        f"期望 200，实际 {resp.status_code}: {resp.text}"
    )
    assert "application/json" in resp.headers.get("content-type", ""), (
        f"Content-Type 非 JSON: {resp.headers.get('content-type')}"
    )
    body = resp.json()
    assert set(body.keys()) == {"items", "next_cursor", "has_more"}, (
        f"SnapshotPage 键集不符: {sorted(body.keys())}"
    )
    assert isinstance(body["items"], list), f"items 应为数组: {body['items']!r}"
    assert type(body["has_more"]) is bool, f"has_more 应为 JSON 布尔: {body['has_more']!r}"
    assert body["next_cursor"] is None or isinstance(body["next_cursor"], str), (
        f"next_cursor 应为字符串或 null: {body['next_cursor']!r}"
    )

    for item in body["items"]:
        assert set(item.keys()) == SNAP_KEYS, (
            f"SnapshotView 键集不符: {sorted(item.keys())}"
        )
        for key in ("id", "request_id", "captured_at", "upstream_url"):
            assert isinstance(item[key], str), f"{key} 应为字符串: {item[key]!r}"
        for key in ("backend_model", "model", "deployment_id"):
            assert item[key] is None or isinstance(item[key], str), (
                f"{key} 应为字符串或 null: {item[key]!r}"
            )
        if item["http_status"] is not None:
            assert isinstance(item["http_status"], int) and 100 <= item["http_status"] <= 599, (
                f"http_status 越界: {item['http_status']!r}"
            )
        if item["latency_ms"] is not None:
            assert isinstance(item["latency_ms"], (int, float)) and item["latency_ms"] >= 0, (
                f"latency_ms 应为 >=0 数值: {item['latency_ms']!r}"
            )
        if item["error_summary"] is not None:
            assert isinstance(item["error_summary"], str), (
                f"error_summary 应为字符串或 null: {item['error_summary']!r}"
            )
            assert len(item["error_summary"].encode("utf-8")) <= 256, (
                f"error_summary 超 256B: {len(item['error_summary'].encode('utf-8'))}"
            )
        assert item["snapshot_type"] in SNAPSHOT_TYPES, (
            f"snapshot_type 越枚举: {item['snapshot_type']!r}"
        )

    raw = resp.text
    for literal in SECRET_LITERALS:
        assert literal not in raw, f"响应含未脱敏字面 {literal!r}"
    for item in body["items"]:
        assert "?" not in item["upstream_url"], (
            f"upstream_url 未去 query: {item['upstream_url']!r}"
        )
