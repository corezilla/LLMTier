"""Case ID: DP-USAGE-07

Endpoint: GET /v1/usage（分页 cursor 重放）
Upstream Provider: provider_local (m5air OMLX bge-m3)
Model: Embedding-v1
Auth: Bearer dev-data

TS-002 依赖：
  Endpoint: http://192.168.1.9:8181（m5air 已部署实例）
  前置写: 4 次 POST /v1/embeddings（固定 body），窗口为紧致动态窗口
  动态窗口: now() 生成（禁止硬编码）；分页全程 from/to 逐字节不变

目标（VRC-MGMT-006 / T-MET-PAGE / CON-METER-004 / INV-6）：同一 usage cursor
重放返回同一冻结 record version 成员：后续页重放逐字段相同（含 record_version），
不新建 snapshot、不推进 head；首屏冻结后新增记录对旧页不可见。

断言：
- page2 与其两次重放：data 逐字段相等（含 request_id、record_version）
- snapshot_id 恒为首屏 sid
- page1 之后新增的 rid_4 不出现在 cursor 重放结果中
- 对照：新快照（无 cursor）中可见 rid_4
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

EMBED_BODY = {"model": "Embedding-v1", "input": "page probe"}
BEYOND_END_OFFSET = 100000


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _embed(api_client) -> str:
    resp = api_client.post("/v1/embeddings", json=EMBED_BODY)
    assert resp.status_code == 200, f"embeddings 失败: {resp.status_code}: {resp.text}"
    rid = resp.headers.get("X-Request-ID")
    assert rid, "embeddings 响应缺 X-Request-ID"
    return rid


@pytest.mark.api_a
def test_dp_usage_07_cursor_replay_idempotent(api_client):
    now = datetime.now(timezone.utc)
    since, until = _iso(now - timedelta(minutes=5)), _iso(now + timedelta(minutes=1))
    window = {"from": since, "to": until}

    rid_1, rid_2, rid_3 = _embed(api_client), _embed(api_client), _embed(api_client)
    our_ids = {rid_1, rid_2, rid_3}

    page1 = api_client.get("/v1/usage", params={**window, "limit": 1})
    assert page1.status_code == 200, f"page1 失败: {page1.status_code}: {page1.text}"
    body1 = page1.json()
    sid = body1["snapshot_id"]
    cursor = body1.get("next_cursor") or f"{sid}:1"

    page2 = api_client.get("/v1/usage", params={**window, "limit": 1, "cursor": cursor})
    assert page2.status_code == 200, f"page2 失败: {page2.text}"
    body2 = page2.json()
    assert body2["snapshot_id"] == sid, "page2 应复用首屏 snapshot"

    # Replay #1
    replay1 = api_client.get("/v1/usage", params={**window, "limit": 1, "cursor": cursor})
    assert replay1.status_code == 200, f"重放#1 失败: {replay1.text}"
    body_r1 = replay1.json()
    assert body_r1["data"] == body2["data"], (
        f"重放#1 与原页逐字段不等:\n{body_r1['data']}\n!=\n{body2['data']}")
    assert body_r1["snapshot_id"] == sid
    assert body_r1["next_cursor"] == body2["next_cursor"]
    assert body_r1["has_more"] == body2["has_more"]

    # Insert a 4th record after the first page froze.
    rid_4 = _embed(api_client)
    assert rid_4 not in our_ids

    # Replay #2 — the frozen page must be unaffected by rid_4 (INV-6).
    replay2 = api_client.get("/v1/usage", params={**window, "limit": 1, "cursor": cursor})
    assert replay2.status_code == 200, f"重放#2 失败: {replay2.text}"
    body_r2 = replay2.json()
    assert body_r2["data"] == body2["data"], "旧页受新增记录影响（INV-6 破坏）"
    assert all(r["request_id"] != rid_4 for r in body_r2["data"]), (
        f"rid_4 泄漏进旧页: {body_r2['data']}")

    # Control: a fresh snapshot (no cursor) does include rid_4. Filter by
    # request_id: the shared window exceeds one page and pages are ordered
    # ascending, so a wide fresh page may not reach the newest row.
    fresh = api_client.get("/v1/usage", params={**window, "request_id": rid_4})
    assert fresh.status_code == 200, f"新快照失败: {fresh.text}"
    fresh_ids = {r["request_id"] for r in fresh.json()["data"]}
    assert rid_4 in fresh_ids, f"rid_4 应出现在新快照中: {fresh_ids}"

    # Last-page invariant on the SAME frozen snapshot. m5air is shared, so the
    # window holds background traffic and walking limit=1 to exhaustion is not
    # bounded; an offset beyond the frozen member count deterministically yields
    # the terminal page (empty data, has_more=false, next_cursor=null).
    end = api_client.get(
        "/v1/usage",
        params={**window, "limit": 1, "cursor": f"{sid}:{BEYOND_END_OFFSET}"},
    )
    assert end.status_code == 200, f"越界 cursor 失败: {end.text}"
    end_body = end.json()
    assert end_body["snapshot_id"] == sid, "越界页 snapshot_id 漂移"
    assert end_body["data"] == [], f"越界 offset 应返回空页: {end_body['data']}"
    assert end_body["has_more"] is False, f"越界 offset 应 has_more=false: {end_body['has_more']}"
    assert end_body["next_cursor"] is None, (
        f"末页 has_more=false 但 next_cursor 非 null: {end_body['next_cursor']!r}"
    )
