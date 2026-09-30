"""Case ID: DP-USAGE-03

Endpoint: GET /v1/usage?limit=1（沿 cursor 分页）
Upstream Provider: provider_local (m5air OMLX bge-m3)
Model: Embedding-v1
Auth: Bearer dev-data

TS-002 依赖：
  Endpoint: http://192.168.1.9:8181（m5air 已部署实例）
  前置写: 2 次 POST /v1/embeddings（固定 body）
  窗口: 紧致动态窗口（now-5min .. now+1min，+1min 头部余量避免边界竞态）

目标（VRC-MGMT-006 / T-MET-PAGE / CON-METER-004）：limit=1 分页沿 cursor 推进，
跨页 snapshot_id/snapshot_at 不变、按 (recorded_at,request_id) 稳定、无重复；
末页 has_more=false ⇒ next_cursor=null；自建记录在新快照中无遗漏。

注：m5air 为共享实例，紧致窗口内仍有背景流量（数百条），"逐页走到真正末页"
不有界；末页 invariant 用同一冻结快照的 **越界 offset cursor** 确定性触发，
跨页稳定性用有界页遍历（≤ WALK_PAGES）。自建记录的无遗漏用 limit=200 的新快照核对。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from tests.system.api_test_v03.constants import iso_sec

EMBED_BODY = {"model": "Embedding-v1", "input": "page-probe-dp-usage-03"}
WALK_PAGES = 5
BEYOND_END_OFFSET = 100000


def _embed(api_client) -> str:
    resp = api_client.post("/v1/embeddings", json=EMBED_BODY)
    assert resp.status_code == 200, f"embeddings 失败: {resp.status_code}: {resp.text}"
    rid = resp.headers.get("X-Request-ID")
    assert rid, "embeddings 响应缺 X-Request-ID"
    return rid


@pytest.mark.api_a
def test_dp_usage_03_pagination(api_client):
    now = datetime.now(timezone.utc)
    since, until = iso_sec(now - timedelta(minutes=5)), iso_sec(now + timedelta(minutes=1))
    window = {"from": since, "to": until}

    rid_a, rid_b = _embed(api_client), _embed(api_client)
    our_rids = {rid_a, rid_b}

    page = api_client.get("/v1/usage", params={**window, "limit": 1})
    assert page.status_code == 200, f"page1 失败: {page.status_code}: {page.text}"
    body = page.json()
    sid = body["snapshot_id"]
    snap_at = body["snapshot_at"]
    assert isinstance(sid, str) and sid, f"page1 snapshot_id 非法: {sid!r}"
    assert isinstance(snap_at, str) and snap_at, f"page1 snapshot_at 非法: {snap_at!r}"
    assert isinstance(body["has_more"], bool), f"has_more 非 bool: {body['has_more']!r}"

    # Bounded walk: snapshot frozen, pages advance and differ.
    prev_rid = body["data"][0]["request_id"] if body["data"] else None
    seen: list[str] = [prev_rid] if prev_rid else []
    cursor = body["next_cursor"]
    assert isinstance(cursor, str) and cursor.startswith(f"{sid}:"), (
        f"has_more=true ⇒ next_cursor 应为 <sid>:<off>，实际 {cursor!r}"
    )
    for page_no in range(1, WALK_PAGES):
        resp = api_client.get("/v1/usage", params={**window, "limit": 1, "cursor": cursor})
        assert resp.status_code == 200, f"page{page_no+1} 失败: {resp.text}"
        current = resp.json()
        assert current["snapshot_id"] == sid, "跨页 snapshot_id 漂移（冻结破坏）"
        assert current["snapshot_at"] == snap_at, "跨页 snapshot_at 漂移"
        rows = current["data"]
        assert len(rows) <= 1, f"page{page_no+1} data 超过 limit=1: {rows}"
        if not rows:
            break
        rid = rows[0]["request_id"]
        assert rid != prev_rid, f"相邻页 request_id 相同（游标未推进）: {rid}"
        assert rid not in seen, f"跨页重复 request_id: {rid}"
        seen.append(rid)
        prev_rid = rid
        if current["has_more"] is False:
            assert current["next_cursor"] is None, "末页 has_more=false 但 next_cursor 非 null"
            break
        cursor = current["next_cursor"]

    # Terminal invariant, deterministically: an offset beyond the frozen member
    # count yields an empty, terminal page on the SAME snapshot.
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

    # No-loss/no-dup for our own records: the window holds background traffic
    # ordered ascending, so a wide fresh page can be truncated before our newest
    # rows. Filter by request_id instead (deterministic, exactly one head row).
    for rid in our_rids:
        one = api_client.get("/v1/usage", params={**window, "request_id": rid})
        assert one.status_code == 200, f"查询 {rid} 失败: {one.text}"
        rows = [r for r in one.json()["data"] if r["request_id"] == rid]
        assert len(rows) == 1, f"自建记录 {rid} 应恰 1 条（无遗漏不重复）: {rows}"
