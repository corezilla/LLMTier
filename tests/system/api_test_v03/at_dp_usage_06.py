"""Case ID: DP-USAGE-06

Endpoint: GET /v1/usage（多主体凭据）
Upstream Provider: provider_local (m5air OMLX bge-m3)
Model: Embedding-v1
Auth: Bearer dev-data（+ X-Principal-ID 区分主体）/ Bearer dev-admin

TS-002 依赖：
  Endpoint: http://192.168.1.9:8181（m5air 已部署实例）
  动态窗口: constants.recent_window()
  前置写: POST /v1/embeddings（固定 body）

目标（VRC-MGMT-006 / T-TRUST-SHARED / R-MET-02）：Usage 主体隔离——
各主体只见到本主体 record，admin 见全局，data 结果 ⊆ admin 结果；
跨主体 cursor 重放 → 403 permission_denied（code 为准）。

【实现 vs 设计偏差（已登记）】
adm-usage-06.md §2/§3 设计用 `admin_client`（Bearer dev-admin）发
POST /v1/embeddings 构造 admin 主体 record。但 `app.py:232` 的 embeddings 路由
走 `self._auth()`（默认 role="data"），admin 凭据会被拒绝（403 permission_denied）——
embeddings 是 data-plane 写入，不接受 admin 凭据。故本脚本改用**两个不同 data 主体**
（同一 `Bearer dev-data` + 不同 `X-Principal-ID`）来演示主体隔离：主体 A 只见自身记录、
不见主体 B；admin 全局可见；data ⊆ admin；跨主体 cursor 重放 403。语义等价且对当前
code 有效。

断言：
- rid_a：主体 A（X-Principal-ID=a）见 1 条；admin 见 1 条
- rid_b：主体 A 见 0 条（data==[]）；admin 见 1 条
- 子集：主体 A 宽查询中可见的**自建 rid 集合** == {rid_a}，且 ⊆ admin 的
  {rid_a, rid_b}（共享实例记录远超一页，两个各自截断的首页不可比）
- 主体 A 产生的 cursor 以 admin 重放 → 403 permission_denied
"""
from __future__ import annotations

import uuid

import pytest

from tests.system.api_test_v03.constants import recent_window

EMBED_BODY = {"model": "Embedding-v1", "input": "isolation probe"}


def _request_ids(page: dict) -> set[str]:
    return {r.get("request_id") for r in (page.get("data") or [])}


@pytest.mark.api_a
def test_dp_usage_06_subject_isolation(api_client, admin_client):
    since, until = recent_window()
    window = {"from": since, "to": until}

    # Two distinct data principals distinguished by X-Principal-ID (explicit creds).
    principal_a = f"consumer-{uuid.uuid4().hex[:8]}"
    principal_b = f"consumer-{uuid.uuid4().hex[:8]}"
    headers_a = {"X-Principal-ID": principal_a}
    headers_b = {"X-Principal-ID": principal_b}

    emb_a = api_client.post("/v1/embeddings", json=EMBED_BODY, headers=headers_a)
    assert emb_a.status_code == 200, f"主体A embeddings 失败: {emb_a.status_code}: {emb_a.text}"
    rid_a = emb_a.headers.get("X-Request-ID")
    assert rid_a, "主体A embeddings 响应缺 X-Request-ID"

    emb_b = api_client.post("/v1/embeddings", json=EMBED_BODY, headers=headers_b)
    assert emb_b.status_code == 200, f"主体B embeddings 失败: {emb_b.status_code}: {emb_b.text}"
    rid_b = emb_b.headers.get("X-Request-ID")
    assert rid_b, "主体B embeddings 响应缺 X-Request-ID"
    assert rid_a != rid_b, "两主体 request_id 意外相同"

    # Subject A sees its own record.
    own = api_client.get("/v1/usage", params={**window, "request_id": rid_a}, headers=headers_a)
    assert own.status_code == 200, f"主体A 查询 rid_a 失败: {own.text}"
    assert _request_ids(own.json()) == {rid_a}, (
        f"主体A 应恰好见自身记录 rid_a: {own.json()['data']}")

    # Subject A must NOT see subject B's record (isolation; empty array, not 403).
    other = api_client.get("/v1/usage", params={**window, "request_id": rid_b}, headers=headers_a)
    assert other.status_code == 200, f"主体A 查询 rid_b 失败: {other.text}"
    assert other.json()["data"] == [], (
        f"主体A 不应见主体B 记录 rid_b: {other.json()['data']}")

    # admin sees both principals' records.
    admin_a = admin_client.get("/v1/usage", params={**window, "request_id": rid_a})
    assert admin_a.status_code == 200, f"admin 查询 rid_a 失败: {admin_a.text}"
    assert rid_a in _request_ids(admin_a.json()), (
        f"admin 应见 rid_a: {admin_a.json()['data']}")
    admin_b = admin_client.get("/v1/usage", params={**window, "request_id": rid_b})
    assert admin_b.status_code == 200, f"admin 查询 rid_b 失败: {admin_b.text}"
    assert rid_b in _request_ids(admin_b.json()), (
        f"admin 应见 rid_b: {admin_b.json()['data']}")

    # Subset check: subject A's result set ⊆ admin's result set.
    #
    # The shared m5air window holds far more than one page and pages are
    # ordered by recorded_at *ascending*, so a plain wide GET returns the
    # oldest page — A's freshly created row (and admin's view of it) need not
    # appear in either truncated page. Comparing two independently truncated
    # pages is therefore unsound (and was the original failure). The isolation
    # contract is instead asserted over the request_ids this test created,
    # using deterministic per-request_id queries: every rid A can see, admin
    # must also see.
    our_rids = {rid_a, rid_b}
    data_wide = api_client.get("/v1/usage", params={**window, "limit": 200}, headers=headers_a)
    assert data_wide.status_code == 200, f"主体A 宽查询失败: {data_wide.text}"
    data_visible = _request_ids(data_wide.json()) & our_rids
    assert data_visible == {rid_a}, (
        f"主体A 应恰好见自身记录 rid_a，实际可见: {data_visible}")

    # admin sees both principals' freshly created records (deterministic filter).
    admin_visible = set()
    for rid in our_rids:
        page = admin_client.get("/v1/usage", params={**window, "request_id": rid})
        assert page.status_code == 200, f"admin 查询 {rid} 失败: {page.text}"
        admin_visible |= _request_ids(page.json())
    assert data_visible <= admin_visible, (
        f"主体隔离破坏：data 可见记录不在 admin 结果集: {data_visible - admin_visible}")
    assert admin_visible == our_rids, (
        f"admin 应见两主体全部记录，实际可见: {admin_visible}")

    # cross-principal cursor replay: a data cursor replayed with admin -> 403.
    first = api_client.get("/v1/usage", params={**window, "limit": 1}, headers=headers_a)
    assert first.status_code == 200, f"主体A 首屏失败: {first.text}"
    first_body = first.json()
    cursor = first_body.get("next_cursor") or f"{first_body['snapshot_id']}:0"

    replay = admin_client.get("/v1/usage", params={**window, "limit": 1, "cursor": cursor})
    assert replay.status_code == 403, (
        f"跨主体 cursor 重放期望 403，实际 {replay.status_code}: {replay.text}")
    err = replay.json().get("error") or {}
    assert err.get("code") == "permission_denied", f"code != permission_denied: {err}"
    assert err.get("type") == "request_error", f"type != request_error: {err}"
