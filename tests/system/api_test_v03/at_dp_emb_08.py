"""Case ID: DP-EMB-08

Endpoint: POST /v1/embeddings
Upstream Provider: prov_b（LAN fake provider，backend_model="slow-embeddings"）
Model: Senior（指向 depl_b）
Auth: Bearer dev-data

TS-002 依赖：
  Endpoint: 临时 LLMTier 实例（llmtier_b_emb_slow），127.0.0.1:<临时端口>
  上游: LAN fake provider（fake_provider_b），慢 embeddings 门控
  Auth: Bearer dev-data

目标：验证 Embeddings 数据面准入饱和 → 429 rate_limit_exceeded + Retry-After。

断言：
- 并发超过 1 许可 + 32 队列上限后，至少一个请求 429
- error.code == "rate_limit_exceeded"、type == "request_error"、retryable is True
- error 键集恰 5 键
- 响应含 Retry-After 头，值为正整数秒

实现：src/inference/routing.py::Router.admit（队列满 → 429 Retry-After:30）。
慢上游由 fake provider 的门控保证占住唯一并发槽；teardown 释放门控，无残留。
"""
from __future__ import annotations

import re
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

import pytest

N_CONCURRENT = 40
ERROR_KEYS = {"message", "type", "code", "param", "retryable"}


@pytest.mark.api_b
def test_dp_emb_08_admission_saturation_429(llmtier_b_emb_slow, fake_provider_b):
    fake_provider_b.reset_slow()
    client = llmtier_b_emb_slow.api_client()
    body = {"model": "Senior", "input": "hello"}

    def _post():
        return client.post("/v1/embeddings", json=body)

    executor = ThreadPoolExecutor(max_workers=N_CONCURRENT)
    try:
        futures = [executor.submit(_post) for _ in range(N_CONCURRENT)]
        # Queue-full rejections return immediately; the occupying request and the
        # queued ones block on the slow upstream gate until the fixture releases.
        wait(futures, timeout=6, return_when=FIRST_COMPLETED)
        responses = [f.result() for f in futures if f.done()]

        rejected = [r for r in responses if r.status_code == 429]
        assert rejected, (
            "准入饱和后未观测到 429（饱和构造失败）："
            f"status 分布={[r.status_code for r in responses]}"
        )

        resp = rejected[0]
        assert resp.headers.get("content-type", "").startswith("application/json")
        err = resp.json().get("error") or {}
        assert err.get("code") == "rate_limit_exceeded", f"error.code 不符: {err}"
        assert err.get("type") == "request_error", f"error.type 不符: {err}"
        assert err.get("retryable") is True, f"error.retryable 非 True: {err}"
        assert err.get("param") is None, f"error.param 非 null: {err}"
        assert set(err) == ERROR_KEYS, f"error 键集不符: {sorted(err)}"

        retry_after = resp.headers.get("retry-after")
        assert retry_after is not None, "429 响应缺少 Retry-After 头"
        assert re.fullmatch(r"[1-9][0-9]*", retry_after.strip()), (
            f"Retry-After 非正整数秒: {retry_after!r}"
        )
    finally:
        fake_provider_b.release_slow()
        executor.shutdown(wait=True)
        client.close()
