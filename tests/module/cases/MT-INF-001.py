"""MT-INF-001 — ResponsesService 组装后推理契约（M003，层①，normal，P0）。

组装保证：校验→路由→适配→终态全链（内部单元真实）；SSE 事件子集对照
OpenAPI、恰好一个 terminal；usage 落账本（measured）。
"""
from __future__ import annotations

import json
import unittest

from tests.common.fakes import FakeAdapter
from tests.module.cases.support.http_env import LoopbackEnv

BODY = {"model": "Worker", "input": "hello", "stream": True, "store": False}


class ResponsesContractTests(LoopbackEnv):
    def _sse_events(self, body=BODY):
        self.fx.app.responses._test_adapter = FakeAdapter(usage=True)
        try:
            conn, response = self.post_sse(body)
            try:
                raw = response.read()
            finally:
                conn.close()
            return response.status, response.headers, raw
        finally:
            self.fx.app.responses._test_adapter = None

    def test_full_chain_produces_single_terminal(self):
        status, headers, raw = self._sse_events()
        self.assertEqual(200, status)
        events = []
        for block in raw.decode().split("\n\n"):
            for line in block.splitlines():
                if line.startswith("data: ") and line != "data: [DONE]":
                    events.append(json.loads(line[6:]))
        types = [e["type"] for e in events]
        self.assertEqual("response.created", types[0])
        terminals = [t for t in types if t in {"response.completed", "response.failed", "response.incomplete"}]
        self.assertEqual(["response.completed"], terminals)
        self.assertEqual(types[-1], terminals[0])
        # OpenAPI 子集：事件类型均在契约面
        allowed = {"response.created", "response.output_item.added", "response.output_item.done",
                   "response.output_text.delta", "response.refusal.delta", "response.reasoning_text.delta",
                   "response.reasoning_summary_text.delta", "response.reasoning_summary_part.done",
                   "response.function_call_arguments.delta", "response.function_call_arguments.done",
                   "response.completed", "response.failed", "response.incomplete"}
        self.assertTrue(set(types) <= allowed, set(types) - allowed)

    def test_usage_measured_in_ledger(self):
        _, headers, _ = self._sse_events()
        request_id = headers["X-Request-ID"]
        rows = self.fx.app.usage.page("trusted-lan-consumer", None, 50, admin=True,
                                      since="2000-01-01T00:00:00Z", until="2100-01-01T00:00:00Z")["data"]
        row = next(r for r in rows if r["request_id"] == request_id)
        self.assertTrue(row["is_final"])
        self.assertEqual("measured", row["measurement_status"])
        self.assertEqual((2, 1, 3), (row["input_tokens"], row["output_tokens"], row["total_tokens"]))

    def test_unsupported_store_true_rejected(self):
        status, payload, _ = self.request("POST", "/v1/responses", body={**BODY, "store": True})
        self.assertEqual(400, status)
        self.assertEqual("unsupported_request", payload["error"]["code"])


if __name__ == "__main__":
    unittest.main()
