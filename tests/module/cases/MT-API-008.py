"""MT-API-008 — SSE terminal 三态（M001，层②/层③ K2，recovery，P0）。

三态：正常流→`completed` trace（created 首帧、terminal 唯一、[DONE] 收尾）；
客户端断开→`aborted(client disconnected)`；流异常（边界替身注入毒载荷）→
`aborted(stream_error)` 且落日志。上游＝FakeAdapter（llmtier-unit-fakes）。
"""
from __future__ import annotations

import json
import unittest
import urllib.error
import urllib.request

from inference.providers.base import ProviderResult
from tests.common.fakes import FakeAdapter
from tests.module.cases.support.http_env import LargeFakeAdapter, LoopbackEnv

BODY = {"model": "Worker", "input": "hello", "stream": True, "store": False}


class SseTerminalTests(LoopbackEnv):
    def _frames(self, raw):
        events = []
        for block in raw.decode().split("\n\n"):
            for line in block.splitlines():
                if line.startswith("data: "):
                    if line == "data: [DONE]":
                        events.append("[DONE]")
                    else:
                        events.append(json.loads(line[6:])["type"])
        return events

    def _trace(self, request_id):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/v1/trace/{request_id}")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())

    def _log_events(self, event):
        page = self.fx.app.logs.page(since="2000-01-01T00:00:00Z", until="2100-01-01T00:00:00Z")
        return [row for row in page["data"] if row["event"] == event]

    def test_completed_terminal_state(self):
        self.fx.app.responses._test_adapter = FakeAdapter(usage=True)
        try:
            conn, response = self.post_sse(BODY)
            try:
                raw = response.read()
            finally:
                conn.close()
            self.assertEqual(200, response.status)
            request_id = response.headers["X-Request-ID"]
            events = self._frames(raw)
            self.assertEqual("response.created", events[0])
            self.assertEqual("[DONE]", events[-1])
            terminals = [e for e in events if e.startswith("response.completed")]
            self.assertEqual(1, len(terminals))
            # 终态按「阶段集合」判定，不按位置：src 的 `ORDER BY stage_timestamp,id`
            # 在同毫秒内退化为随机 uuid4 序（见报告：trace 阶段无因果序保证），
            # 所以 `stages[-1]` 不是合法 oracle。
            trace = self._trace(request_id)
            stages = [s["stage"] for s in trace["stages"]]
            self.assertEqual({"received", "validated", "routed", "upstream_started",
                              "upstream_ended", "completed"}, set(stages))
            self.assertNotIn("aborted", stages)
        finally:
            self.fx.app.responses._test_adapter = None

    def test_client_abort_is_aborted_client_disconnected(self):
        self.fx.app.responses._test_adapter = LargeFakeAdapter()
        try:
            sock, _, request_id = self.raw_post_sse(BODY)
            self.drain(sock)
            sock.close()
            trace = self.wait_for(lambda: (lambda t: t if any(s["stage"] == "aborted" for s in t["stages"]) else None)(self._try_trace(request_id)))
            self.assertIsNotNone(trace)
            aborted = next(s for s in trace["stages"] if s["stage"] == "aborted")
            self.assertEqual("client disconnected", aborted["detail"]["reason"])
        finally:
            self.fx.app.responses._test_adapter = None

    def test_stream_poison_is_aborted_stream_error_and_logged(self):
        # 边界替身注入契约违规载荷（非对象 output）→ 响应流组装抛 AttributeError
        self.fx.app.responses._test_adapter = _PoisonAdapter()
        try:
            conn, response = self.post_sse(BODY)
            request_id = response.headers["X-Request-ID"]
            raw = b""
            try:
                raw = response.read()
            except (urllib.error.URLError, OSError, http_client_exceptions()):
                pass
            finally:
                conn.close()
            self.assertNotEqual(500, response.status)
            trace = self.wait_for(lambda: (lambda t: t if any(s["stage"] == "aborted" for s in t["stages"]) else None)(self._try_trace(request_id)))
            self.assertIsNotNone(trace)
            aborted = next(s for s in trace["stages"] if s["stage"] == "aborted")
            self.assertEqual("stream_error", aborted["detail"]["reason"])
            self.assertTrue(self._log_events("stream_error"))
        finally:
            self.fx.app.responses._test_adapter = None

    def _try_trace(self, request_id):
        try:
            return self._trace(request_id)
        except urllib.error.HTTPError:
            return {"stages": []}


class _PoisonAdapter(FakeAdapter):
    def complete(self, model, request):
        result = super().complete(model, request)
        return ProviderResult(["not-a-dict"], result.usage, result.provider_request_id, status=result.status)


def http_client_exceptions():
    import http.client
    return (http.client.IncompleteRead, http.client.HTTPException)


if __name__ == "__main__":
    unittest.main()
