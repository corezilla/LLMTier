"""Case ID: ST-resp-020

Endpoint: POST /v1/responses；GET /v1/runtime
Upstream Provider: prov_b（LAN fake provider，backend_model="slow-responses"，门控占槽）
Model: Senior（指向 depl_b）
Auth: Bearer dev-data

TS-002 依赖：
  Endpoint: 临时 LLMTier 实例（llmtier_b_resp_slow），127.0.0.1:<临时端口>
  上游: LAN fake provider（fake_provider_b）；slow-responses 在 provider 侧阻塞占住唯一槽
  Auth: Bearer dev-data

目标：准入饱和（许可 1 + 队列 32）→ 至少一个 429 rate_limit_exceeded + Retry-After。

确定性构造（不依赖并发完成时序）：
  1. fake provider 门控关闭（reset）；backend_model="slow-responses" 使上游阻塞。
  2. 发**一个**请求占住唯一槽；轮询 GET /v1/runtime 直到 depl_b.running >= 1（槽确证被占）。
  3. 再并发发 N 个请求：前 32 个入队，其余（队列已满）立即 429。
  4. 断言至少一个 429 + error identity + Retry-After 正整数。
  5. teardown：release 门控 → 占槽请求与队列请求立即排空，无残留长睡眠。

断言：
- GET /v1/runtime 曾观测到 depl_b.running >= 1（占槽证据）
- 至少一个并发请求 429
- error.code == "rate_limit_exceeded"、type == "request_error"
- retryable is True、param is None、键集恰 5 键
- 429 响应含 Retry-After 头且为正整数秒
"""
from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

N_CONCURRENT = 40
ERROR_KEYS = {"message", "type", "code", "param", "retryable"}


def _wait_slot_held(inst, timeout: float = 10.0) -> None:
    """Poll /v1/runtime until depl_b shows an in-flight request (the gate holder)."""
    admin = inst.admin_client()
    try:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            resp = admin.get("/v1/runtime")
            assert resp.status_code == 200, f"/v1/runtime 返回 {resp.status_code}: {resp.text}"
            running = (resp.json().get("deployments", {}).get("depl_b") or {}).get("running", 0)
            if running >= 1:
                return
            time.sleep(0.05)
        raise AssertionError("占槽请求未在超时内确证占用许可（/v1/runtime running==0）")
    finally:
        admin.close()


@pytest.mark.api_b
def test_dp_resp_20_admission_saturation_429(llmtier_b_resp_slow, fake_provider_b):
    fake_provider_b.reset_slow()
    admin = llmtier_b_resp_slow.admin_client()
    client = llmtier_b_resp_slow.api_client()
    executor = ThreadPoolExecutor(max_workers=N_CONCURRENT + 1)
    holder = None
    try:
        body = {
            "model": "Senior",
            "input": [{"role": "user", "content": "hi"}],
            "stream": True,
            "store": False,
        }

        # 1) 先占住唯一槽（上游门控阻塞，持槽直到 teardown release）。
        holder = executor.submit(lambda: client.post("/v1/responses", json=body))
        _wait_slot_held(llmtier_b_resp_slow)

        # 2) 槽已确证被占：再发 N 个并发；队列上限 32，其余（队列已满）**立即** 429。
        #    队列内的 32 个会阻塞等待许可（最多 30s），不阻塞在它们身上：只等首个 429。
        futures = [executor.submit(lambda: client.post("/v1/responses", json=body))
                   for _ in range(N_CONCURRENT)]
        resp = None
        deadline = time.monotonic() + 15
        try:
            for future in as_completed(futures, timeout=max(0.1, deadline - time.monotonic())):
                r = future.result()
                if r.status_code == 429:
                    resp = r
                    break
        except TimeoutError:
            pass
        assert resp is not None, (
            "准入饱和后未在窗口内观测到 429（饱和构造失败）"
        )

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
        # 释放门控：占槽与排队请求立即排空，无残留长睡眠。
        fake_provider_b.release_slow()
        executor.shutdown(wait=True)
        client.close()
        admin.close()
