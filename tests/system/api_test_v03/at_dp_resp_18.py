"""Case ID: ST-resp-018

Endpoint: POST /v1/responses
Upstream Provider: 无（上限检查在读取前拒绝 >2 MiB）
Model: Senior（边界子测走 depl_b）
Auth: Bearer dev-data

TS-002 依赖：
  Endpoint: 临时 LLMTier 实例（llmtier_b），127.0.0.1:<临时端口>
  上游: LAN fake provider（fake_provider_b）——仅边界子测使用
  Auth: Bearer dev-data

目标：Content-Length > 2 MiB → 413 request_too_large；恰好 2 MiB 不受本上限拒绝。

实现：src/http_api/app.py `_body()`
  if length > 2 * 1024 * 1024: raise ApiError(413, "request_too_large", ...)

断言：
- >2 MiB：HTTP 413 + code "request_too_large" + type "request_error" + param null
  + retryable False + 键集恰 5 键
- ==2 MiB（边界）：精确断言"不被上限拒绝且被受理"——HTTP 200 + text/event-stream
  （合法 ResponsesRequest 经路由到 fake provider）。若边界误判为 413 即 FAIL；
  任一其它错误（500 等）亦 FAIL，不再用 `code != request_too_large` 的宽松门。
"""
from __future__ import annotations

import json

import pytest

ERROR_KEYS = {"message", "type", "code", "param", "retryable"}
MAX_BODY = 2 * 1024 * 1024


def _oversized_body() -> bytes:
    body = {
        "model": "Senior",
        "input": [{"role": "user", "content": "a" * (MAX_BODY + 1)}],
        "stream": True,
        "store": False,
    }
    raw = json.dumps(body).encode()
    assert len(raw) > MAX_BODY
    return raw


def _exact_body() -> bytes:
    body = {
        "model": "Senior",
        "input": [{"role": "user", "content": "a"}],
        "stream": True,
        "store": False,
    }
    pad = MAX_BODY - len(json.dumps(body).encode())
    assert pad > 0
    body["input"][0]["content"] = "a" * (1 + pad)
    raw = json.dumps(body).encode()
    assert len(raw) == MAX_BODY, f"边界 body 长度 {len(raw)} != {MAX_BODY}"
    return raw


@pytest.mark.api_b
def test_dp_resp_18_body_too_large(api_client_b):
    raw = _oversized_body()
    resp = api_client_b.post(
        "/v1/responses",
        content=raw,
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 413, f"期望 413，实际 {resp.status_code}: {resp.text}"
    assert resp.headers.get("content-type", "").startswith("application/json")
    body = resp.json()
    err = body.get("error") or {}
    assert err.get("code") == "request_too_large", f"error.code 不符: {err}"
    assert err.get("type") == "request_error", f"error.type 不符: {err}"
    assert err.get("param") is None, f"error.param 非 null: {err}"
    assert err.get("retryable") is False, f"error.retryable 非 False: {err}"
    assert set(err) == ERROR_KEYS, f"error 键集不符: {sorted(err)}"


@pytest.mark.api_b
def test_dp_resp_18_exact_two_mib_accepted(api_client_b):
    raw = _exact_body()
    assert len(raw) == MAX_BODY, f"边界 body 长度 {len(raw)} != {MAX_BODY}"
    resp = api_client_b.post(
        "/v1/responses",
        content=raw,
        headers={"Content-Type": "application/json"},
    )
    # 边界语义：恰好 2 MiB **不**触发 >2MiB 上限，合法请求被受理 → 200 + SSE。
    assert resp.status_code == 200, (
        f"恰好 2 MiB 应被受理（200 + SSE），实际 {resp.status_code}: {resp.text[:200]}"
    )
    content_type = resp.headers.get("content-type", "")
    assert content_type.startswith("text/event-stream"), (
        f"边界受理应返回 SSE：content-type={content_type!r}"
    )
    assert "response.completed" in resp.text, "边界受理流缺 response.completed"
