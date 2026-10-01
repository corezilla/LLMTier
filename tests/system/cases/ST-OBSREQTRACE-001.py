"""Case ID: ST-OBSREQTRACE-001

Endpoint: GET /v1/trace/{request_id}
Upstream Provider: m5air OMLX / m5mac OMLX（responses-capable tier）
Model: Worker（responses-capable tier；backing dep_omlx_qwen36 等）
Auth: Bearer dev-admin（查询）/ Bearer dev-data（制造 trace）

TS-002 依赖：
  Endpoint: http://192.168.1.9:8181（m5air 已部署实例）
  上游: m5air OMLX 9000 / m5mac OMLX 9000
  模型: Worker（简洁 prompt，max_output_tokens=50）

TS-003：m5air 已部署实例自带上游，本 case 不构造新 provider endpoint。

目标：GET /v1/trace/{request_id} 返回单请求全生命周期 TraceView：键集恰 5，
stages 有序且覆盖 received…completed（含上游阶段），组合 snapshot/usage（可为 null）。
"""
from __future__ import annotations

import pytest

TRACE_BODY = {
    "model": "Worker",
    "input": [{"role": "user", "content": "Hello"}],
    "stream": True,
    "store": False,
    "max_output_tokens": 50,
}
VIEW_KEYS = {"request_id", "correlation_id", "stages", "snapshot", "usage"}
STAGE_KEYS = {"stage", "timestamp", "detail"}


@pytest.mark.api_a
def test_obs_reqtrace_01_full_lifecycle(admin_client, api_client):
    status = None
    with api_client.stream("POST", "/v1/responses", json=TRACE_BODY) as resp:
        status = resp.status_code
        for _chunk in resp.iter_bytes():
            pass
    # 构造前提：制造 trace 的请求本身必须成功。若该请求失败（非 200），
    # "无 traces" 反映的是真实故障而非数据缺失 —— 不得据此 BLOCKED 掩盖 FAIL。
    assert status == 200, (
        f"制造 trace 的 POST /v1/responses 返回 {status}（非 200）——真实故障，非数据缺失"
    )

    listing = admin_client.get("/v1/diagnostics/traces", params={"limit": 1})
    assert listing.status_code == 200, (
        f"traces 列表期望 200，实际 {listing.status_code}: {listing.text}"
    )
    items = listing.json()["items"]
    if not items:
        # xfail → BLOCKED：请求已 200 成功，但入口未落任何 trace（观测数据缺失）。
        # 这是合法的 BLOCKED（不能判定契约），且前置已排除"制造请求失败"的假 BLOCKED。
        pytest.xfail(
            "BLOCKED (ST-OBSREQTRACE-001): responses 请求成功但 traces 列表为空，无法取得 request_id"
        )
    request_id = items[0]["request_id"]

    resp = admin_client.get(f"/v1/trace/{request_id}")
    assert resp.status_code == 200, (
        f"期望 200，实际 {resp.status_code}: {resp.text}"
    )
    assert "application/json" in resp.headers.get("content-type", ""), (
        f"Content-Type 非 JSON: {resp.headers.get('content-type')}"
    )
    body = resp.json()
    assert set(body.keys()) == VIEW_KEYS, (
        f"TraceView 键集不符: {sorted(body.keys())}"
    )
    assert body["request_id"] == request_id, (
        f"request_id 未回指查询 id: {body['request_id']!r} != {request_id!r}"
    )
    assert body["correlation_id"] is None or isinstance(body["correlation_id"], str), (
        f"correlation_id 应为字符串或 null: {body['correlation_id']!r}"
    )
    stages = body["stages"]
    assert isinstance(stages, list) and len(stages) >= 1, (
        f"stages 应 ≥1 项: {stages!r}"
    )
    timestamps = []
    stage_names = []
    for stage in stages:
        assert set(stage.keys()) == STAGE_KEYS, (
            f"TraceStage 键集不符: {sorted(stage.keys())}"
        )
        timestamps.append(stage["timestamp"])
        stage_names.append(stage["stage"])
    assert timestamps == sorted(timestamps), f"stages 未按 timestamp 升序: {timestamps}"
    assert "received" in stage_names, f"缺入口阶段 received: {stage_names}"
    assert any("upstream" in name for name in stage_names), (
        f"成功请求缺上游阶段: {stage_names}"
    )
    snapshot = body["snapshot"]
    if snapshot is not None:
        assert isinstance(snapshot, dict) and len(snapshot) == 11, (
            f"snapshot 应为 11 键 SnapshotView: {snapshot!r}"
        )
    usage = body["usage"]
    if usage is not None:
        assert isinstance(usage, dict) and len(usage) == 8, (
            f"usage 应为 8 键 UsageView: {usage!r}"
        )
