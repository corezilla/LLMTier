"""Case ID: ST-OBSTRACE-003

Endpoint: GET /v1/diagnostics/traces
Upstream Provider: 无（仅诊断读面；不触上游）
Model: 无
Auth: Bearer dev-admin

TS-002 依赖：
  Endpoint: 专用临时 LLMTier 实例（llmtier_b_diag_store，独立临时 SQLite/端口）
  上游: 无（本 case 不触上游）
  模型: 无

TS-003：不触上游，无 provider endpoint。

目标：诊断 store 不可用时 GET /v1/diagnostics/traces 返回 503
usage_store_unavailable（typed server error），不得以 200/空结果冒充
"无数据"；恢复存储后回到 200。

技法（同 ST-USAGE-008）：把 SQLite 三件套移开并在原 db 路径 mkdir 成目录，
使 sqlite3.connect 失败；finally 恢复。
"""
from __future__ import annotations

import pytest

TRACE_PATH = "/v1/diagnostics/traces"


@pytest.mark.api_b
def test_obs_trace_03_store_unavailable_503(llmtier_b_diag_store, store_triplet):
    inst = llmtier_b_diag_store
    client = inst.admin_client()
    breaker = store_triplet(inst.db_path)
    try:
        baseline = client.get(TRACE_PATH)
        assert baseline.status_code == 200, (
            f"基线期望 200，实际 {baseline.status_code}: {baseline.text}"
        )
        body = baseline.json()
        assert set(body.keys()) == {"items", "next_cursor", "has_more"}, (
            f"基线体键集不符: {sorted(body.keys())}"
        )

        breaker.break_store()
        assert inst.db_path.is_dir(), "db_path 应是占位目录"

        fault = client.get(TRACE_PATH)
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
        recovered = client.get(TRACE_PATH)
        client.close()
    assert recovered.status_code == 200, (
        f"恢复后期望 200，实际 {recovered.status_code}: {recovered.text}"
    )
    rbody = recovered.json()
    assert set(rbody.keys()) == {"items", "next_cursor", "has_more"}, (
        f"恢复体键集不符: {sorted(rbody.keys())}"
    )
