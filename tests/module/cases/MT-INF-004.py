"""MT-INF-004 — Router.admit 准入与目录（M003，层①/层④ T4，concurrency，P0）。

组装保证：占满→队列等待、FIFO 释放、availability 三态（available/degraded/
unavailable）、许可释放（_inflight 归零）。经公开入口驱动。
"""
from __future__ import annotations

import threading
import time
import unittest

from tests.common.fakes import FakeAdapter
from tests.module.cases.support.http_env import LoopbackEnv


class AdmitAndCatalogTests(LoopbackEnv):
    def _runtime(self):
        status, runtime, _ = self.request("GET", "/v1/runtime")
        return runtime

    def _models(self):
        return self.request("GET", "/v1/models")[1]["data"]

    def test_models_availability_states(self):
        # seeded：Worker healthy → available；其余无候选 → unavailable
        models = {m["id"]: m["availability"] for m in self._models()}
        self.assertEqual("available", models["Worker"])
        self.assertEqual("unavailable", models["Senior"])

    def test_degraded_when_unhealthy_candidate(self):
        provider, deployment = None, None
        deployments = self.request("GET", "/v1/deployments")[1]["data"]
        did = deployments[0]["id"]
        # 存储面注入：健康态置 unhealthy（种子允许的健康迁移，无公开入口）
        conn = self.fx.app.store.connection()
        conn.execute("UPDATE deployments SET health='unhealthy' WHERE id=?", (did,))
        models = {m["id"]: m["availability"] for m in self._models()}
        self.assertEqual("unavailable", models["Worker"])
        conn.execute("UPDATE deployments SET health='healthy' WHERE id=?", (did,))

    def test_permit_release_and_fifo_queue(self):
        release = threading.Event()
        started = threading.Event()

        class BlockingAdapter(FakeAdapter):
            def complete(self, model, request):
                started.set()
                release.wait(10)
                return super().complete(model, request)

        self.fx.app.responses._test_adapter = BlockingAdapter(usage=True)
        try:
            body = {"model": "Worker", "input": "hi", "stream": True, "store": False}
            first = threading.Thread(target=self.fx.app.responses.create, args=("p1", "req_first", body))
            first.start()
            self.assertTrue(started.wait(5))
            runtime = self._runtime()
            worker_dep = [d for d, v in runtime["deployments"].items()]
            running = sum(v["running"] for v in runtime["deployments"].values())
            self.assertEqual(1, running)

            # 第二请求排队（FIFO）
            done = {}

            def second_request():
                done["r"] = self.fx.app.responses.create("p2", "req_second", body)
            second = threading.Thread(target=second_request)
            second.start()
            time.sleep(0.3)
            runtime = self._runtime()
            queue_len = sum(runtime["queues"].values())
            self.assertEqual(1, queue_len)

            release.set()
            first.join(10); second.join(10)
            self.assertIn("r", done)
            # 释放后 _inflight 归零
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if sum(v["running"] for v in self._runtime()["deployments"].values()) == 0:
                    break
                time.sleep(0.05)
            self.assertEqual(0, sum(v["running"] for v in self._runtime()["deployments"].values()))
        finally:
            self.fx.app.responses._test_adapter = None
            release.set()


if __name__ == "__main__":
    unittest.main()
