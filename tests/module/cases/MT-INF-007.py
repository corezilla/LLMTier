"""MT-INF-007 — 准入四出口（M003，层②/层④ T5，concurrency，P0）。

出口：无候选→404 `model_not_found`；队列≥32→429 `Retry-After: 30`；
全不健康→503 `model_unavailable`；队列等待超时→429 `Retry-After: 1`
（受控时钟，见 MT-INF-018）。经公开入口 + 线程对偶。
"""
from __future__ import annotations

import threading
import time
import unittest

from http_api.errors import ApiError
from tests.common.fakes import FakeAdapter
from tests.module.cases.support.inference_env import RESPONSE_BODY, InferenceEnv


class AdmissionTests(InferenceEnv):
    def _create(self, model="Senior", adapter=None):
        self.fx.app.responses._test_adapter = adapter or FakeAdapter()
        try:
            return self.fx.app.responses.create("consumer", "req_admit", {**RESPONSE_BODY, "model": model})
        finally:
            self.fx.app.responses._test_adapter = None

    def test_no_candidates_is_404_model_not_found(self):
        # 未知 tier：Registry 404 → 映射 model_not_found
        with self.assertRaises(ApiError) as cm:
            self._create(model="NoSuchTier")
        self.assertEqual(("model_not_found", 404), (cm.exception.code, cm.exception.status))

    def test_empty_tier_is_unsupported_model_before_admit(self):
        # 空 tier（无候选）：能力档 responses=false → 400 unsupported_model（先于准入）
        with self.assertRaises(ApiError) as cm:
            self._create(model="Junior")
        self.assertEqual("unsupported_model", cm.exception.code)

    def test_all_unhealthy_is_503_model_unavailable(self):
        did = self.senior["id"]
        conn = self.fx.app.store.connection()
        conn.execute("UPDATE deployments SET health='unhealthy' WHERE id=?", (did,))
        try:
            with self.assertRaises(ApiError) as cm:
                self._create()
            self.assertEqual(("model_unavailable", 503), (cm.exception.code, cm.exception.status))
        finally:
            conn.execute("UPDATE deployments SET health='healthy' WHERE id=?", (did,))

    def test_queue_full_is_429_retry_after_30(self):
        release = threading.Event()
        started = threading.Event()

        class BlockingAdapter(FakeAdapter):
            def complete(self, model, request):
                started.set(); release.wait(30); return super().complete(model, request)

        self.fx.app.responses._test_adapter = BlockingAdapter()
        errors = []
        def fill(_n):
            try:
                self.fx.app.responses.create("consumer", f"req_fill_{_n}", RESPONSE_BODY)
            except ApiError as exc:
                errors.append(exc)
        try:
            holder = threading.Thread(target=fill, args=(0,)); holder.start()
            self.assertTrue(started.wait(5))
            queue_fillers = [threading.Thread(target=fill, args=(i + 1,)) for i in range(32)]
            for t in queue_fillers: t.start()
            # 确定性：等队列恰好填满 32（Router.snapshot 公开 seam 观测）
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if sum(self.fx.app.router.snapshot()["queues"].values()) >= 32:
                    break
                time.sleep(0.02)
            self.assertGreaterEqual(sum(self.fx.app.router.snapshot()["queues"].values()), 32)
            # 第 33 个 → 429 Retry-After: 30
            with self.assertRaises(ApiError) as cm:
                self.fx.app.responses.create("consumer", "req_overflow", RESPONSE_BODY)
            self.assertEqual(("rate_limit_exceeded", 429), (cm.exception.code, cm.exception.status))
            self.assertEqual("30", cm.exception.headers["Retry-After"])
        finally:
            release.set()

    def test_queue_wait_keeps_order_until_capacity(self):
        release = threading.Event()
        started = threading.Event()

        class BlockingAdapter(FakeAdapter):
            def complete(self, model, request):
                started.set(); release.wait(10); return super().complete(model, request)

        self.fx.app.responses._test_adapter = BlockingAdapter()
        holder_result, waiter_result = {}, {}
        def run(target, bucket):
            def go():
                try:
                    bucket["ok"] = self.fx.app.responses.create("consumer", target, RESPONSE_BODY)
                except ApiError as exc:
                    bucket["err"] = exc
            return go
        try:
            holder = threading.Thread(target=run("req_holder", holder_result)); holder.start()
            self.assertTrue(started.wait(5))
            waiter = threading.Thread(target=run("req_waiter", waiter_result)); waiter.start()
            time.sleep(0.3)
            # 未超时前保持排队：无错误、无结果
            self.assertNotIn("err", waiter_result)
            self.assertNotIn("ok", waiter_result)
            release.set()
            holder.join(10); waiter.join(10)
            self.assertIn("ok", holder_result)
            self.assertIn("ok", waiter_result)
        finally:
            release.set()


if __name__ == "__main__":
    unittest.main()
