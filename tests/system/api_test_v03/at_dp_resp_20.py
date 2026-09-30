"""Case ID: DP-RESP-20

Endpoint: POST /v1/responses；诊断注入 PATCH /v1/deployments/depl_b/diagnostics
Upstream Provider: prov_b（LAN fake provider）；slot 由 delay 注入占用
Model: Senior（指向 depl_b）
Auth: Bearer dev-data / dev-admin

TS-002 依赖：
  Endpoint: 临时 LLMTier 实例（llmtier_b_diag），127.0.0.1:<临时端口>
  上游: LAN fake provider（fake_provider_b）；delay 注入在 admit 内 sleep 占槽
  Auth: Bearer dev-data

目标：准入饱和（许可 1 + 队列 32）→ 至少一个 429 rate_limit_exceeded + Retry-After。

实现：src/inference/routing.py:77-78（队列满 → 429, Retry-After:30）；
      delay 注入在 `with router.admit(model)` 内 time.sleep（src/inference/responses.py:119-120）。

断言：
- 至少一个并发请求 429
- error.code == "rate_limit_exceeded"、type == "request_error"
- retryable is True、param is None、键集恰 5 键
- 429 响应含 Retry-After 头且为正整数秒
- teardown：PATCH {"items": []} 清空注入
"""
from __future__ import annotations

import re
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

import pytest

N_CONCURRENT = 40
ERROR_KEYS = {"message", "type", "code", "param", "retryable"}


@pytest.mark.api_b
def test_dp_resp_20_admission_saturation_429(llmtier_b_diag):
    admin = llmtier_b_diag.admin_client()
    endpoint = "/v1/deployments/depl_b/diagnostics"
    injection = {
        "items": [{"type": "delay", "config": {"delay_ms": 60000}, "enabled": True}]
    }
    client = llmtier_b_diag.api_client()
    executor = ThreadPoolExecutor(max_workers=N_CONCURRENT)
    try:
        set_resp = admin.patch(endpoint, json=injection)
        assert set_resp.status_code == 200, (
            f"写入 delay 注入失败: {set_resp.status_code}: {set_resp.text}"
        )
        assert any(
            item.get("type") == "delay" and item.get("enabled")
            for item in set_resp.json()
        ), f"delay 注入未生效: {set_resp.json()}"

        body = {
            "model": "Senior",
            "input": [{"role": "user", "content": "hi"}],
            "stream": True,
            "store": False,
        }

        def _post():
            return client.post("/v1/responses", json=body)

        futures = [executor.submit(_post) for _ in range(N_CONCURRENT)]
        wait(futures, timeout=8, return_when=FIRST_COMPLETED)
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
        clear = admin.patch(endpoint, json={"items": []})
        assert clear.status_code == 200, f"清空注入失败: {clear.status_code}: {clear.text}"
        remaining = admin.get(endpoint)
        assert remaining.status_code == 200
        assert all(not item.get("enabled") for item in remaining.json()), (
            f"注入未清空: {remaining.json()}"
        )
        executor.shutdown(wait=False)
        client.close()
        admin.close()
