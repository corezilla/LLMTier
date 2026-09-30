"""Case ID: OBS-SNAP-02

Endpoint: GET /v1/diagnostics/snapshots
Upstream Provider: 无（仅诊断读面；不触上游）
Model: 无
Auth: Bearer dev-admin

TS-002 依赖：
  Endpoint: 专用临时 LLMTier 实例（llmtier_b，独立临时 SQLite/端口）
  上游: prov_b 指向 LAN IP 上的 fake provider（TS-003）
  模型: depl_b（backend_model=test-model）

TS-003：本 case 不触发推理，无 provider endpoint 请求。

目标：GET /v1/diagnostics/snapshots 提交无效/过期 cursor：HTTP 400 cursor_expired
（ERR-CURSOR），不返回被游标解引用为零匹配的"假空页"。

注（实现 vs case doc，见报告 discrepancy）：case doc 断言当前实现"不校验 cursor"
（§1 契约一致性警示）；实测 `snapshots_page` 已对不存在 cursor 抛
ApiError(400,"cursor_expired")（`src/libdiag/snapshots.py:49-51`）。本脚本按实现
（也是契约期望）断言 400。
"""
from __future__ import annotations

import pytest

SNAP_PATH = "/v1/diagnostics/snapshots"


@pytest.mark.api_b
def test_obs_snap_02_invalid_cursor_400(llmtier_b):
    client = llmtier_b.admin_client()
    for cursor in ("not-a-real-cursor", "snap_deadbeef0000000000000000000000"):
        resp = client.get(SNAP_PATH, params={"cursor": cursor})
        assert resp.status_code == 400, (
            f"cursor={cursor!r} 期望 400，实际 {resp.status_code}: {resp.text}"
        )
        err = resp.json()["error"]
        assert set(err.keys()) == {"message", "type", "code", "param", "retryable"}, (
            f"错误信封键集不符: {sorted(err.keys())}"
        )
        assert err["code"] == "cursor_expired", f"cursor={cursor!r} code 不符: {err}"
        assert err["type"] == "request_error", f"cursor={cursor!r} type 不符: {err}"
        assert err["retryable"] is False, f"cursor={cursor!r} retryable 应为 False: {err}"

    control = client.get(SNAP_PATH, params={"limit": 1})
    assert control.status_code == 200, (
        f"正相对照期望 200，实际 {control.status_code}: {control.text}"
    )
    assert set(control.json().keys()) == {"items", "next_cursor", "has_more"}, (
        f"正相对照页键集不符: {sorted(control.json().keys())}"
    )
    client.close()
