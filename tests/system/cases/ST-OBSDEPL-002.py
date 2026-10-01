"""Case ID: ST-OBSDEPL-002

Endpoint: PATCH /v1/deployments/{deployment_id}/diagnostics
Upstream Provider: prov_b（LAN IP fake provider，TS-003）
Model: depl_b（backend_model=test-model）
Auth: Bearer dev-admin

TS-002 依赖：
  Endpoint: 专用临时 LLMTier 实例（llmtier_b，独立临时 SQLite/端口）
  上游: prov_b 指向 LAN IP 上的 fake provider（TS-003）
  模型: depl_b / test-model

TS-003：本 case 不触发推理，无 provider endpoint 请求。

目标：PATCH /v1/deployments/{id}/diagnostics 写入故障注入：HTTP 200 + 更新后的
InjectionView[]，按 (deployment_id, type) upsert 生效，副作用 = 同事务审计。
teardown 清空。
"""
from __future__ import annotations

import pytest

DIAG_PATH = "/v1/deployments/depl_b/diagnostics"
ITEM_KEYS = {"id", "deployment_id", "type", "config", "enabled", "updated_at"}


def _views(resp):
    assert resp.status_code == 200, (
        f"期望 200，实际 {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert isinstance(body, list), f"顶层应为 InjectionView[]: {body!r}"
    for item in body:
        assert set(item.keys()) == ITEM_KEYS, (
            f"InjectionView 键集应恰 6 键: {sorted(item.keys())}"
        )
    return body


@pytest.mark.api_b
def test_obs_depl_02_write_upsert_multi_and_audit(llmtier_b):
    client = llmtier_b.admin_client()
    try:
        client.patch(DIAG_PATH, json={"items": []})
        assert _views(client.get(DIAG_PATH)) == [], "初始注入应为空"

        written = _views(client.patch(
            DIAG_PATH,
            json={"items": [{"type": "delay", "config": {"delay_ms": 2000}, "enabled": True}]},
        ))
        assert len(written) == 1, f"写入后应恰 1 项: {written}"
        delay = written[0]
        assert delay["type"] == "delay" and delay["config"].get("delay_ms") == 2000, (
            f"delay 写入不符: {delay}"
        )
        assert delay["enabled"] is True and delay["deployment_id"] == "depl_b", (
            f"deployment/enabled 不符: {delay}"
        )

        reread = _views(client.get(DIAG_PATH))
        assert [i["config"].get("delay_ms") for i in reread if i["type"] == "delay"] == [2000], (
            f"写入未持久化: {reread}"
        )

        updated = _views(client.patch(
            DIAG_PATH,
            json={"items": [{"type": "delay", "config": {"delay_ms": 500}, "enabled": True}]},
        ))
        delays = [i for i in updated if i["type"] == "delay"]
        assert len(delays) == 1, f"同 type upsert 不应新增重复项: {delays}"
        assert delays[0]["config"].get("delay_ms") == 500, f"upsert 未更新配置: {delays[0]}"

        multi = _views(client.patch(
            DIAG_PATH,
            json={"items": [
                {"type": "fault_502", "config": {"error_body": "boom"}, "enabled": True},
                {"type": "rate_limit", "config": {"retry_after_sec": 2}, "enabled": False},
            ]},
        ))
        by_type = {i["type"]: i for i in multi}
        assert by_type["fault_502"]["enabled"] is True, f"fault_502 enabled 不符: {by_type['fault_502']}"
        assert by_type["rate_limit"]["enabled"] is False, f"rate_limit 应持久为 disabled: {by_type['rate_limit']}"

        audit = client.get("/v1/audit", params={"limit": 200})
        assert audit.status_code == 200, f"audit 读取失败: {audit.text}"
        hits = [
            r for r in audit.json()["data"]
            if r.get("action") == "diagnostics.injection.update"
            and r.get("target") == "depl_b"
            and r.get("result") == "success"
        ]
        assert hits, "未找到 diagnostics.injection.update 成功审计行"
    finally:
        cleared = client.patch(DIAG_PATH, json={"items": []})
        final = client.get(DIAG_PATH)
        client.close()
    assert cleared.status_code == 200, f"revoke 期望 200: {cleared.text}"
    assert cleared.json() == [], f"revoke 应清空: {cleared.json()}"
    assert final.status_code == 200 and final.json() == [], (
        f"teardown 后应为空: {final.json()}"
    )
