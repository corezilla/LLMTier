"""MT-API-010 — `_correlation` 分支（M001，层②，normal，P1）。

分支：`X-Correlation-ID` 回显；`traceparent` 合法→提取 32-hex；非法→原样；
皆缺→缺省（无 X-Correlation-ID 响应头）。冻结向量：合法 traceparent
`00-<32hex>-<16hex>-01`。经 /v1/responses SSE 真实链路断言。
"""
from __future__ import annotations

import json
import unittest
import urllib.request

from tests.common.fakes import FakeAdapter
from tests.module.cases.support.http_env import LoopbackEnv

BODY = {"model": "Worker", "input": "hello", "stream": True, "store": False}
VALID_TRACEPARENT = "00-471c71d404b3a4c6a7d3e5f1098abcde-00f067aa0ba902b7-01"


class CorrelationTests(LoopbackEnv):
    def setUp(self):
        self.fx.app.responses._test_adapter = FakeAdapter(usage=True)

    def tearDown(self):
        self.fx.app.responses._test_adapter = None

    def _sse(self, headers):
        conn, response = self.post_sse(BODY, headers=headers)
        try:
            response.read()
            return response.headers
        finally:
            conn.close()

    def _trace_correlation(self, request_id):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/v1/trace/{request_id}", timeout=10) as resp:
            return json.loads(resp.read())

    def test_x_correlation_id_echoed(self):
        headers = self._sse({"X-Correlation-ID": "corr-abc-1"})
        self.assertEqual("corr-abc-1", headers.get("X-Correlation-ID"))

    def test_valid_traceparent_extracts_32hex(self):
        headers = self._sse({"traceparent": VALID_TRACEPARENT})
        self.assertEqual("471c71d404b3a4c6a7d3e5f1098abcde", headers.get("X-Correlation-ID"))

    def test_invalid_traceparent_kept_verbatim(self):
        headers = self._sse({"traceparent": "zz-not-a-traceparent"})
        self.assertEqual("zz-not-a-traceparent", headers.get("X-Correlation-ID"))

    def test_missing_both_means_no_header(self):
        headers = self._sse({})
        self.assertIsNone(headers.get("X-Correlation-ID"))

    def test_error_envelope_carries_correlation(self):
        status, payload, headers = self.request("POST", "/v1/responses", body={"model": "Worker"},
                                                headers={"X-Correlation-ID": "corr-err-9"})
        self.assertEqual(400, status)
        self.assertEqual("corr-err-9", headers.get("X-Correlation-ID"))
