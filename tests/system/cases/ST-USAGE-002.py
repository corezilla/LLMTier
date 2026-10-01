"""Case ID: ST-USAGE-002

Endpoint: POST /v1/embeddings（前置写）; GET /v1/usage（读取）
Upstream Provider: provider_local (m5air OMLX bge-m3)
Model: Embedding-v1
Auth: Bearer dev-data

TS-002 依赖：
  Endpoint: http://192.168.1.9:8181（m5air 已部署实例）
  动态窗口: constants.recent_window()
  前置写: POST /v1/embeddings（固定 body）

目标（T-MET-FINAL / VRC-MGMT-006）：一次成功请求后，其 request_id 在同一窗口的
GET /v1/usage 中**自含**可见，记录为 head 终态（is_final=true），endpoint/model 与
调用一致；head 单条不累加；unknown ⇒ token 全 null（非 0）。

断言：
- 前置 embeddings 200 且 X-Request-ID 非空
- GET /v1/usage?request_id=<rid>：200；data 恰 1 条且 request_id==rid（head 唯一）
- endpoint=="/v1/embeddings"、model=="Embedding-v1"、is_final is True、record_version>=1
- UsageRecord 键集/枚举/时间戳；unknown ⇒ token null；recorded_at ∈ [from,to)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from tests.system.constants import (
    assert_usage_record,
    iso_sec,
    parse_ts,
)

EMBED_BODY = {"model": "Embedding-v1", "input": "llmtier-usage-02-probe"}


@pytest.mark.api_a
def test_dp_usage_02_has_records(api_client):
    emb = api_client.post("/v1/embeddings", json=EMBED_BODY)
    assert emb.status_code == 200, f"前置 embeddings 失败: {emb.status_code}: {emb.text}"
    rid = emb.headers.get("X-Request-ID")
    assert rid, "embeddings 响应缺 X-Request-ID"

    now = datetime.now(timezone.utc)
    since, until = iso_sec(now - timedelta(minutes=5)), iso_sec(now + timedelta(minutes=5))
    resp = api_client.get(
        "/v1/usage",
        params={"from": since, "to": until, "request_id": rid},
    )
    assert resp.status_code == 200, f"返回 {resp.status_code}: {resp.text}"
    body = resp.json()
    data = body["data"]
    records = [r for r in data if r["request_id"] == rid]
    assert len(records) == 1, (
        f"同一 request_id 的 head 记录应恰 1 条（不累加），实际 {len(records)}: {data}"
    )
    record = records[0]
    assert record["request_id"] == rid
    assert record["endpoint"] == "/v1/embeddings", f"endpoint 不符: {record['endpoint']!r}"
    assert record["model"] == "Embedding-v1", f"model 不符: {record['model']!r}"
    assert record["is_final"] is True, f"终态记录 is_final 必须 True: {record}"
    assert record["record_version"] >= 1, f"record_version < 1: {record['record_version']}"

    assert_usage_record(record, where="usage record")

    lo, hi = parse_ts(since), parse_ts(until)
    assert lo <= parse_ts(record["recorded_at"]) < hi, (
        f"recorded_at={record['recorded_at']} 越界 [from,to)"
    )
