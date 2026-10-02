"""MT-INF-018 — 并发超时 + 许可泄漏分支（M003，层②，concurrency，P1；§1.5.1 c8）。

受控时钟（plan §1 受控时钟资产口径：patch `inference.routing.time`）：
`Router.admit` 队列等待超 30s → 429 `rate_limit_exceeded` + `Retry-After: 1`；
`_inflight` 归零、无许可泄漏（后续请求成功）。
"""
from __future__ import annotations

import threading
import time
import unittest
from unittest.mock import patch

from http_api.errors import ApiError
from tests.common.fakes import FakeAdapter
from tests.module.cases.support.inference_env import RESPONSE_BODY, InferenceEnv


class FakeClock:
    def __init__(self, now=1000.0):
        self.now = now
        self._lock = threading.Lock()

    def monotonic(self):
        with self._lock:
            return self.now

    def advance(self, seconds):
        with self._lock:
            self.now += seconds


class QueueTimeoutTests(InferenceEnv):
    def _prime_provider_interval(self, ms=1000):
        """公开入口 PATCH：给 provider 设 min_request_interval_ms，使 waiter 首轮
        condition.wait 落在 provider 节流窗（真实 ~1s）内，受控时钟可在窗内推进。"""
        providers = self.fx.app.registry.list_providers()
        cloud = next(p for p in providers if p["name"] == "cloud-Senior")
        _, etag = self.fx.app.registry.get_provider(cloud["id"])
        self.fx.app.registry.update_provider(cloud["id"], {"usage": {"min_request_interval_ms": ms}}, etag)

    def _run_timeout_scenario(self, request_id_holder, request_id_waiter):
        release = threading.Event()
        started = threading.Event()

        class BlockingAdapter(FakeAdapter):
            def complete(self, model, request):
                started.set(); release.wait(30); return super().complete(model, request)

        clock = FakeClock(now=1000.0)
        errors = {}

        def waiter():
            try:
                self.fx.app.responses.create("consumer", request_id_waiter, RESPONSE_BODY)
            except ApiError as exc:
                errors["exc"] = exc

        self._prime_provider_interval()
        self.fx.app.responses._test_adapter = BlockingAdapter()
        try:
            holder = threading.Thread(target=self.fx.app.responses.create, args=("consumer", request_id_holder, RESPONSE_BODY))
            with patch("inference.routing.time", clock):
                holder.start()
                self.assertTrue(started.wait(5))
                waiter_thread = threading.Thread(target=waiter)
                waiter_thread.start()
                # 等 waiter 入队；其首轮 wait＝provider 节流窗（~1s 真实），窗内推进受控时钟
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    if sum(self.fx.app.router.snapshot()["queues"].values()) >= 1:
                        break
                    time.sleep(0.01)
                clock.advance(31)
                waiter_thread.join(15)
            release.set()
            holder.join(15)
        finally:
            release.set()
        return errors

    def test_queue_wait_timeout_is_429_retry_after_1(self):
        errors = self._run_timeout_scenario("req_clock_holder", "req_clock_waiter")
        self.assertIn("exc", errors)
        exc = errors["exc"]
        self.assertEqual(("rate_limit_exceeded", 429), (exc.code, exc.status))
        self.assertEqual("1", exc.headers["Retry-After"])
        self.assertTrue(exc.retryable)

    def test_no_permit_leak_after_timeout(self):
        errors = self._run_timeout_scenario("req_leak_holder", "req_leak_waiter")
        self.assertIn("exc", errors)
        # 释放后 inflight 归零，且新请求成功（无许可泄漏）
        release = threading.Event()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            snapshot = self.fx.app.router.snapshot()
            if sum(v["running"] for v in snapshot["deployments"].values()) == 0:
                break
            time.sleep(0.05)
        self.assertEqual(0, sum(v["running"] for v in self.fx.app.router.snapshot()["deployments"].values()))
        self.fx.app.responses._test_adapter = FakeAdapter(usage=True)
        try:
            result = self.fx.app.responses.create("consumer", "req_after_leak", RESPONSE_BODY)
        finally:
            self.fx.app.responses._test_adapter = None
        self.assertEqual("completed", result["status"])


if __name__ == "__main__":
    unittest.main()
