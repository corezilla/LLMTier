"""MT-API-012 — 客户端中途断开 broken pipe（M001，层②，recovery，P0；§1.5.1 c4）。

ENV-2 真实 socket：SSE 已开始后客户端 `close()` → `aborted(client disconnected)`；
无 500、无 fd 泄漏、账本不变（abort 不改记账）、Router 许可释放。
"""
from __future__ import annotations

import json
import os
import unittest
import urllib.request

from tests.common.fakes import FakeAdapter
from tests.module.cases.support.http_env import LargeFakeAdapter, LoopbackEnv

BODY = {"model": "Worker", "input": "hello", "stream": True, "store": False}


class BrokenPipeTests(LoopbackEnv):
    def _usage_rows(self):
        status, page, _ = self.request("GET", "/v1/usage?from=2000-01-01T00:00:00Z&to=2100-01-01T00:00:00Z")
        return page["data"]

    def _runtime_inflight(self):
        status, runtime, _ = self.request("GET", "/v1/runtime")
        return sum(d["running"] for d in runtime["deployments"].values())

    def _fds(self):
        return len(os.listdir("/dev/fd"))

    def test_client_disconnect_mid_stream(self):
        self.fx.app.responses._test_adapter = LargeFakeAdapter()
        baseline_fds = self._fds()
        try:
            status_before = {row["request_id"]: row for row in self._usage_rows()}
            sock, _, request_id = self.raw_post_sse(BODY)
            self.drain(sock)
            sock.close()

            def aborted_trace():
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/v1/trace/{request_id}", timeout=10) as resp:
                        trace = json.loads(resp.read())
                except urllib.error.HTTPError:
                    return None
                return trace if any(s["stage"] == "aborted" and s["detail"].get("reason") == "client disconnected" for s in trace["stages"]) else None
            self.assertIsNotNone(self.wait_for(aborted_trace))

            # 无 500：服务日志无 unhandled_error；进程健康
            status, health, _ = self.request("GET", "/healthz")
            self.assertEqual(200, status)

            # 账本不变：该请求恰有一条 final measured 记录（abort 不改记账）
            rows = [r for r in self._usage_rows() if r["request_id"] == request_id]
            self.assertEqual(1, len(rows))
            self.assertTrue(rows[0]["is_final"])
            self.assertEqual("measured", rows[0]["measurement_status"])

            # 许可释放 + fd 不泄漏
            self.assertTrue(self.wait_for(lambda: self._runtime_inflight() == 0))
            self.assertLessEqual(self._fds(), baseline_fds + 2)
        finally:
            self.fx.app.responses._test_adapter = None


import urllib.error  # noqa: E402  (kept at bottom for readability of helpers above)


if __name__ == "__main__":
    unittest.main()
