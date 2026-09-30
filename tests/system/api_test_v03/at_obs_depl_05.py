"""Case ID: OBS-DEPL-05

Endpoint: PATCH /v1/deployments/depl_b/diagnostics
Upstream Provider: 无（注入配置写面；不触上游）
Model: 无
Auth: Bearer dev-admin

TS-002 依赖：
  Endpoint: 专用临时 LLMTier 实例（llmtier_b_diag_store，独立临时 SQLite/端口）
  上游: 无（本 case 不触上游）
  模型: 无

TS-003：不触上游，无 provider endpoint。

目标：诊断 store 不可用时 PATCH /v1/deployments/depl_b/diagnostics 返回 503
usage_store_unavailable（typed server error），不得以 200/空结果冒充
"无数据"；恢复存储后回到 200。

技法（同 DP-USAGE-08）：PATCH 经 AdminService.mutate → store.transaction，
store.transaction 失败由 _run 的 sqlite3.Error 兜底为同码。把 SQLite 三件套
移开并在原 db 路径 mkdir 成目录，使 sqlite3.connect 失败；finally 恢复。
"""
from __future__ import annotations

import pytest

DIAG_PATH = "/v1/deployments/depl_b/diagnostics"
INJECTION_BODY = {
    "items": [
        {"type": "fault_502", "config": {"error_body": "x"}, "enabled": True}
    ]
}


@pytest.mark.api_b
def test_obs_depl_05_store_unavailable_503(llmtier_b_diag_store, store_triplet):
    inst = llmtier_b_diag_store
    client = inst.admin_client()
    breaker = store_triplet(inst.db_path)
    try:
        baseline = client.patch(DIAG_PATH, json=INJECTION_BODY)
        assert baseline.status_code == 200, (
            f"基线期望 200，实际 {baseline.status_code}: {baseline.text}"
        )
        body = baseline.json()
        assert isinstance(body, list), f"基线体应为 InjectionView[]: {body}"
        assert any(item.get("type") == "fault_502" and item.get("enabled") for item in body), (
            f"基线注入未生效: {body}"
        )

        breaker.break_store()
        assert inst.db_path.is_dir(), "db_path 应是占位目录"

        fault = client.patch(DIAG_PATH, json=INJECTION_BODY)
        assert fault.status_code == 503, (
            f"存储不可用时期望 503，实际 {fault.status_code}: {fault.text}"
        )
        err = fault.json()["error"]
        assert set(err.keys()) == {"message", "type", "code", "param", "retryable"}, (
            f"错误信封键集不符: {sorted(err.keys())}"
        )
        assert err["code"] == "usage_store_unavailable", f"code 不符: {err}"
        assert err["type"] == "server_error", f"type 不符: {err}"
    finally:
        breaker.restore()
        recovered = client.patch(DIAG_PATH, json={"items": []})
        # teardown: revoke the baseline injection so no state leaks.
        cleared = client.get(DIAG_PATH)
        client.close()
    assert recovered.status_code == 200, (
        f"恢复后期望 200，实际 {recovered.status_code}: {recovered.text}"
    )
    rbody = recovered.json()
    assert isinstance(rbody, list), f"恢复体应为 InjectionView[]: {rbody}"
    assert cleared.status_code == 200
    assert all(not item.get("enabled") for item in cleared.json()), (
        f"teardown 未清空注入: {cleared.json()}"
    )
