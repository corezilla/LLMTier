"""Case ID: ST-RATELIMIT-001

Endpoint: POST /v1/responses ×6（并发）
Upstream Provider: prov_b（SlowAdapter 进程内替身，max_concurrent_requests=1）
Model: Senior（指向 depl_b）
Auth: Bearer dev-data

TS-002 依赖：
  Endpoint: 临时 LLMTier 实例（llmtier_b_ratelimit），127.0.0.1:<临时端口>
  上游: 无网络调用（LLMTIER_SLOW_ADAPTER_DELAY=1.0 ⇒ ResponsesService 用
        SlowAdapter，每次 complete 阻塞 1s）；
        provider_usage_profiles.max_concurrent_requests=1（单并发许可）
  Auth: Bearer dev-data

目标：验证 provider 并发许可=1 时，6 个并发请求被 32 深队列**吸收**——全部
最终 200，无 429（正向队列排空路径；与 ST-RESP-020 的队列满→429 互补）。

断言：
- 6 个并发请求全部 HTTP 200（队列吸收，无 spurious 429）
- 总耗时 > 4s（许可=1、每次 1s ⇒ 串行排空；证明确实经过队列而非并发直通）
"""
from __future__ import annotations

import re
import threading
import time

import pytest

N_CONCURRENT = 6
RESPONSES_BODY = {
    "model": "Senior",
    "input": [{"role": "user", "content": "hi"}],
    "stream": True,
    "store": False,
    "max_output_tokens": 16,
}


@pytest.mark.api_b
def test_dp_ratelimit_01_queue_absorbs_six(llmtier_b_ratelimit):
    client = llmtier_b_ratelimit.api_client()
    results: list[int] = []
    lock = threading.Lock()

    def one_call() -> None:
        try:
            resp = client.post("/v1/responses", json=RESPONSES_BODY)
            code = resp.status_code
        except Exception:  # noqa: BLE001
            code = -1
        with lock:
            results.append(code)

    start = time.time()
    threads = [threading.Thread(target=one_call) for _ in range(N_CONCURRENT)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.time() - start

    assert len(results) == N_CONCURRENT, f"期望 {N_CONCURRENT} 个结果，实际 {len(results)}"
    for code in results:
        assert code == 200, f"队列应吸收全部请求（无 429）；观测到 {code}"
    assert elapsed > 4.0, (
        f"max_concurrent=1、每次 1s ⇒ 6 个请求应串行排队 >4s；实际 {elapsed:.1f}s"
    )
