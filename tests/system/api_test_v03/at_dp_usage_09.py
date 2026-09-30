"""Case ID: DP-USAGE-09

Endpoint: POST /v1/responses（触发义务）; GET /v1/usage（观察）
Upstream Provider: 无（路径 A 准入失败法：depl_b 未 probe，不触上游）
Model: Senior（指向 depl_b，未 probe 故不健康）
Auth: 触发 Bearer dev-data；查询 Bearer dev-admin

TS-002 依赖：
  Endpoint: 专用临时 LLMTier 实例（llmtier_b_restart，独立临时 SQLite/端口）
  上游: 无（路径 A 不触上游；准入因无健康候选失败）
  模型: Senior（service level，指向未 probe 的 depl_b）

TS-003：路径 A 不触上游，无 provider endpoint。

目标（T-MET-CRASH）：账本核心不变量——authorize_dispatch 在 dispatch 前提交
*义务 + v1 unknown + head=1*（单事务）；此后进程崩溃/重启，该 orphan unknown
仍在且绝不回填为 0；GET /v1/usage 仍返回该 request_id，measurement_status=
unknown、token 全为 NULL、is_final=false。

路径 A（准入失败法）：depl_b 未 probe（health != healthy），POST /v1/responses
经校验后先 authorize_dispatch 提交义务，随后 Router.admit 因无健康候选抛
503 model_unavailable，admitted=False ⇒ 不调 finish ⇒ 库中留 orphan unknown。
重启（同 db_path/settings）后查询验证不变量。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

RESPONSES_BODY = {
    "model": "Senior",
    "input": [{"role": "user", "content": "hi"}],
    "stream": True,
    "store": False,
}


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")


@pytest.mark.api_b
def test_dp_usage_09_orphan_unknown_survives_restart(llmtier_b_restart):
    inst = llmtier_b_restart
    t0 = datetime.now(timezone.utc) - timedelta(minutes=5)
    api = inst.api_client()
    admin = inst.admin_client()
    try:
        # Step 1: trigger the obligation. depl_b is NOT probed -> admission
        # rejects with 503 model_unavailable AFTER authorize_dispatch committed.
        resp = api.post("/v1/responses", json=RESPONSES_BODY)
        assert resp.status_code == 503, (
            f"期望准入失败 503，实际 {resp.status_code}: {resp.text}"
        )
        request_id = resp.headers.get("X-Request-ID")
        assert request_id, "触发响应缺少 X-Request-ID"

        # Step 2: real process restart on the SAME db/settings.
        t1 = datetime.now(timezone.utc) + timedelta(minutes=5)
        inst.restart()
        health = admin.get("/healthz")
        assert health.status_code == 200, f"重启后 /healthz != 200: {health.status_code}"

        # Step 3: query the ledger after restart.
        page = admin.get(
            "/v1/usage",
            params={"from": _iso(t0), "to": _iso(t1), "request_id": request_id},
        )
        assert page.status_code == 200, f"重启后 GET /v1/usage 期望 200: {page.status_code}: {page.text}"
        data = page.json()["data"]
        records = [r for r in data if r["request_id"] == request_id]
        assert records, (
            f"重启后 orphan 记录丢失：request_id={request_id} 不在页中: {data}"
        )
        record = records[0]

        # Step 4: the invariant — unknown, tokens NULL (never 0), not final, v1.
        assert record["measurement_status"] == "unknown", f"measurement_status 不符: {record}"
        assert record["source"] == "unavailable", f"source 不符: {record}"
        assert record["input_tokens"] is None, f"input_tokens 必须为 None（非 0）: {record}"
        assert record["output_tokens"] is None, f"output_tokens 必须为 None（非 0）: {record}"
        assert record["total_tokens"] is None, f"total_tokens 必须为 None（非 0）: {record}"
        assert record["is_final"] is False, f"is_final 必须 False: {record}"
        assert record["record_version"] == 1, f"record_version 必须 1: {record}"
    finally:
        api.close()
        admin.close()
