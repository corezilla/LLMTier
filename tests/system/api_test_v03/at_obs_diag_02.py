"""Case ID: ST-obsdiag-002

Endpoint: PATCH /v1/diagnostics
Upstream Provider: 无（注入开关写面；不触上游）
Model: 无
Auth: Bearer dev-admin

TS-002 依赖：
  Endpoint: 专用临时 LLMTier 实例（llmtier_b，独立临时 SQLite/端口）
  上游: prov_b 指向 LAN IP 上的 fake provider（TS-003）
  模型: depl_b（backend_model=test-model）

TS-003：本 case 不触发推理，不构造 provider endpoint 请求；prov_b 已是 LAN URL。

目标：PATCH /v1/diagnostics 更新全局诊断开关：HTTP 200 + 精确 SwitchState，
部分更新保持缺省键，写入持久化（二次 GET 一致），副作用 = 同事务审计
（action=diagnostics.switch.update，target=diagnostics）。
teardown 恢复原值。
"""
from __future__ import annotations

import pytest


def _switch_state(resp) -> dict:
    assert resp.status_code == 200, (
        f"期望 200，实际 {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert set(body.keys()) == {"snapshots_enabled", "stats_enabled"}, (
        f"SwitchState 键集应恰为 {{snapshots_enabled, stats_enabled}}: {sorted(body.keys())}"
    )
    assert type(body["snapshots_enabled"]) is bool and type(body["stats_enabled"]) is bool, (
        f"SwitchState 两值均应为 JSON 布尔: {body}"
    )
    return body


@pytest.mark.api_b
def test_obs_diag_02_patch_switches_partial_upsert_and_audit(llmtier_b):
    client = llmtier_b.admin_client()
    baseline = client.get("/v1/diagnostics")
    orig = _switch_state(baseline)
    orig_raw = baseline.content
    try:
        target_snapshots = not orig["snapshots_enabled"]

        partial = client.patch("/v1/diagnostics", json={"snapshots_enabled": target_snapshots})
        body = _switch_state(partial)
        assert body["snapshots_enabled"] is target_snapshots, f"部分更新未生效: {body}"
        assert body["stats_enabled"] == orig["stats_enabled"], (
            f"部分更新重置了缺省键 stats_enabled: {body}"
        )

        reread = _switch_state(client.get("/v1/diagnostics"))
        assert reread == body, f"写入未持久化（二次 GET 不一致）: {reread} != {body}"

        full = _switch_state(client.patch(
            "/v1/diagnostics",
            json={"snapshots_enabled": True, "stats_enabled": True},
        ))
        assert full["snapshots_enabled"] is True and full["stats_enabled"] is True, (
            f"全量更新两键未同时为真: {full}"
        )

        empty = _switch_state(client.patch("/v1/diagnostics", json={}))
        assert empty == full, f"空更新应幂等且无值变化: {empty} != {full}"

        audit = client.get("/v1/audit", params={"limit": 200})
        assert audit.status_code == 200, f"audit 读取失败 {audit.status_code}: {audit.text}"
        rows = audit.json()["data"]
        hits = [
            r for r in rows
            if r.get("action") == "diagnostics.switch.update"
            and r.get("target") == "diagnostics"
            and r.get("result") == "success"
            and r.get("actor") == "operator"
        ]
        assert hits, (
            f"未找到 diagnostics.switch.update 成功审计行: {rows[:10]}"
        )
    finally:
        restored = client.patch(
            "/v1/diagnostics",
            json={
                "snapshots_enabled": orig["snapshots_enabled"],
                "stats_enabled": orig["stats_enabled"],
            },
        )
        final = client.get("/v1/diagnostics")
        client.close()
    _switch_state(restored)
    _switch_state(final)
    assert final.content == orig_raw, f"teardown 未恢复到初值: {final.json()} != {orig}"
