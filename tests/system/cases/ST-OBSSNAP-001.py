"""Case ID: ST-OBSSNAP-001

Endpoint: GET /v1/diagnostics/snapshots
Upstream Provider: m5air OMLX / m5mac OMLX / minimax（构造快照需一次 responses 调用）
Model: Worker（responses-capable tier；构造快照数据）
Auth: Bearer dev-admin（读写开关与读面）/ Bearer dev-data（制造快照）

TS-002 依赖：
  Endpoint: http://192.168.1.9:8181（m5air 已部署实例）
  上游: m5air OMLX 9000 / m5mac OMLX 9000 / minimax（responses 调用上游）
  模型: Worker（简洁 prompt，max_output_tokens=16）

TS-003：m5air 已部署实例自带上游，本 case 不构造新 provider endpoint。

目标：GET /v1/diagnostics/snapshots 返回 SnapshotPage：顶层键集恰
{items, next_cursor, has_more}，每项为恰好 11 键的 SnapshotView，且内容已脱敏
（upstream_url 去 query、error_summary ≤256B、不含 Secret/凭据/正文）。

构造（非空断言）：本 case 先 PATCH 打开 `snapshots_enabled`、发起一次
`POST /v1/responses`（上游成功或失败均会落一行快照），使 items 非空后再断言
页/项/脱敏不变量；teardown 恢复原开关值。若构造后仍为空则视为构造失败（FAIL），
不再以"空页合法"放行（消除 vacuous 断言）。
"""
from __future__ import annotations

import re

import pytest

SNAP_PATH = "/v1/diagnostics/snapshots"
DIAG_PATH = "/v1/diagnostics"
SNAP_KEYS = {
    "id", "request_id", "captured_at", "upstream_url", "backend_model",
    "http_status", "latency_ms", "error_summary", "model", "deployment_id",
    "snapshot_type",
}
SNAPSHOT_TYPES = {"upstream", "error"}
# "9832" is a 4-digit token that can coincidentally land inside a hex request-id,
# an RFC3339 timestamp, or a latency_ms value, so it is scanned as a standalone
# alphanumeric token (rejecting neighbours in [0-9A-Za-z]) rather than a bare
# substring. The other needles are unambiguous.
SECRET_LITERALS = ("Authorization", "Bearer ", "secret_ref")
_SECRET_TOKEN_RE = re.compile(r"(?<![0-9A-Za-z])9832(?![0-9A-Za-z])")
TRACE_BODY = {
    "model": "Worker",
    "input": [{"role": "user", "content": "snapshot probe"}],
    "stream": True,
    "store": False,
    "max_output_tokens": 16,
}


def _restore_switches(admin_client, orig_raw: bytes) -> None:
    """Best-effort restore of the pre-case switch bytes via PATCH (teardown)."""
    import json
    orig = json.loads(orig_raw)
    admin_client.patch(
        DIAG_PATH,
        json={
            "snapshots_enabled": orig.get("snapshots_enabled", False),
            "stats_enabled": orig.get("stats_enabled", False),
        },
    )


@pytest.mark.api_a
def test_obs_snap_01_page_shape_and_redaction(admin_client, api_client):
    orig_raw = admin_client.get(DIAG_PATH).content
    try:
        patch = admin_client.patch(DIAG_PATH, json={"snapshots_enabled": True})
        assert patch.status_code == 200, f"打开 snapshots_enabled 失败: {patch.text}"

        with api_client.stream("POST", "/v1/responses", json=TRACE_BODY) as stream:
            for _chunk in stream.iter_bytes():
                pass

        resp = admin_client.get(SNAP_PATH, params={"limit": 50})
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
        assert body["items"], (
            "构造后快照页仍为空——无法验证项级/脱敏契约（构造前提未满足）"
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
        assert not _SECRET_TOKEN_RE.search(raw), "响应含未脱敏 token 字面 '9832'"
        for item in body["items"]:
            assert "?" not in item["upstream_url"], (
                f"upstream_url 未去 query: {item['upstream_url']!r}"
            )
    finally:
        _restore_switches(admin_client, orig_raw)
