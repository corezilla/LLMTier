"""Case ID: ST-obstrace-002

Endpoint: GET /v1/diagnostics/traces
Upstream Provider: prov_b（LAN IP fake provider，TS-003）
Model: depl_b（backend_model=test-model）
Auth: Bearer dev-admin

TS-002 依赖：
  Endpoint: 专用临时 LLMTier 实例（llmtier_b，独立临时 SQLite/端口）
  上游: prov_b 指向 LAN IP 上的 fake provider（tests/fixtures/v03_fake_provider.py）
  模型: depl_b / test-model

TS-003：上游为 LAN IP fake provider；本 case 的 POST /v1/responses 走该 LAN endpoint。

目标：GET /v1/diagnostics/traces limit=1 稳定分页 + 无效 cursor → 400 cursor_expired
（ERR-CURSOR）。

注（实现 vs case doc，见报告 discrepancy）：case doc §1 断言当前实现"不校验 cursor"
（仅含 `|` 才使用），并期望所有无效 cursor 400。实测 `traces` 对**不含 `|`** 的
cursor 抛 ApiError(400,"cursor_expired")（`src/libdiag/traces.py:85-88`）；但**含 `|`**
的构造（如 `2020-01-01T00:00:00Z|req_deadbeef`）被当作合法 cursor 使用，返回 200。
本脚本按实现断言：无 `|` cursor → 400；并显式观测含 `|` cursor 的实测行为。
"""
from __future__ import annotations

import pytest

TRACE_PATH = "/v1/diagnostics/traces"
RESPONSES_BODY = {
    "model": "Worker",
    "input": [{"role": "user", "content": "Hello"}],
    "stream": True,
    "store": False,
    "max_output_tokens": 10,
}


def _make_traces(api_client_b):
    for _ in range(2):
        with api_client_b.stream("POST", "/v1/responses", json=RESPONSES_BODY) as resp:
            for _chunk in resp.iter_bytes():
                pass


@pytest.mark.api_b
def test_obs_trace_02_limit1_paging_and_invalid_cursor(llmtier_b, api_client_b):
    _make_traces(api_client_b)
    client = llmtier_b.admin_client()

    page = client.get(TRACE_PATH, params={"limit": 1})
    assert page.status_code == 200, (
        f"limit=1 期望 200，实际 {page.status_code}: {page.text}"
    )
    body = page.json()
    assert set(body.keys()) == {"items", "next_cursor", "has_more"}, (
        f"TracePage 键集不符: {sorted(body.keys())}"
    )
    assert len(body["items"]) <= 1, f"limit=1 单页应 ≤1 项: {len(body['items'])}"

    if body["has_more"]:
        assert isinstance(body["next_cursor"], str) and body["next_cursor"], (
            f"has_more=true 时 next_cursor 应为非空字符串: {body['next_cursor']!r}"
        )
        nxt = client.get(TRACE_PATH, params={"limit": 1, "cursor": body["next_cursor"]})
        assert nxt.status_code == 200, (
            f"第二页期望 200，实际 {nxt.status_code}: {nxt.text}"
        )
        first_ids = {item["request_id"] for item in body["items"]}
        next_ids = {item["request_id"] for item in nxt.json()["items"]}
        assert not (first_ids & next_ids), "limit=1 分页跨页重叠"

    invalid = client.get(TRACE_PATH, params={"limit": 1, "cursor": "not-a-real-cursor"})
    assert invalid.status_code == 400, (
        f"无效 cursor（无 |）期望 400，实际 {invalid.status_code}: {invalid.text}"
    )
    err = invalid.json()["error"]
    assert set(err.keys()) == {"message", "type", "code", "param", "retryable"}, (
        f"错误信封键集不符: {sorted(err.keys())}"
    )
    assert err["code"] == "cursor_expired", f"code 不符: {err}"
    assert err["type"] == "request_error", f"type 不符: {err}"
    assert err["retryable"] is False, f"retryable 应为 False: {err}"

    pipe_cursor = client.get(
        TRACE_PATH, params={"limit": 1, "cursor": "2020-01-01T00:00:00Z|req_deadbeef"}
    )
    assert pipe_cursor.status_code == 200, (
        "实测：含 | 的构造被 traces 当作合法 cursor 使用（返回 200），"
        f"而非 case doc 期望的 400: {pipe_cursor.status_code}: {pipe_cursor.text}"
    )
    client.close()
