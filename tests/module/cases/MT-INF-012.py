"""MT-INF-012 — 上游配额/额度耗尽映射（M003，层②，recovery，P1；§1.5.1 a22/b1/b3）。

边界替身（loopback FakeUpstream，真实 transport）返回上游配额耗尽 429/402/403
与非配额 4xx：断言沿用上游码 + `code=provider_error`，429→retryable=true、
402/403→false；义务收敛 unknown 不补零；不跨等级 fallback（仅命中所配 tier）。
"""
from __future__ import annotations

import unittest

from http_api.errors import ApiError
from tests.module.cases.support.inference_env import RESPONSE_BODY, InferenceEnv


class QuotaExhaustionTests(InferenceEnv):
    def _expect(self, status, request_id):
        self.upstream.quota_status = status
        self.upstream_mode("quota")
        with self.assertRaises(ApiError) as cm:
            self.fx.app.responses.create("consumer", request_id, RESPONSE_BODY)
        return cm.exception

    def _record(self, request_id):
        return next(r for r in self.usage_rows() if r["request_id"] == request_id)

    def test_upstream_429_is_provider_error_retryable(self):
        exc = self._expect(429, "req_quota_429")
        self.assertEqual((429, "provider_error", True), (exc.status, exc.code, exc.retryable))
        row = self._record("req_quota_429")
        self.assertEqual(("unknown", None), (row["measurement_status"], row["input_tokens"]))

    def test_upstream_402_is_provider_error_not_retryable(self):
        exc = self._expect(402, "req_quota_402")
        self.assertEqual((402, "provider_error", False), (exc.status, exc.code, exc.retryable))

    def test_upstream_403_is_provider_error_not_retryable(self):
        exc = self._expect(403, "req_quota_403")
        self.assertEqual((403, "provider_error", False), (exc.status, exc.code, exc.retryable))

    def test_non_quota_4xx_is_provider_error(self):
        exc = self._expect(422, "req_quota_422")
        self.assertEqual((422, "provider_error", False), (exc.status, exc.code, exc.retryable))

    def test_no_cross_tier_fallback(self):
        # 配额耗尽时不得改道其它候选 tier：Junior（无绑定）不受影响，也无第二次上游命中
        hits_before = self.upstream.hits()
        exc = self._expect(429, "req_quota_fb")
        self.assertEqual(429, exc.status)
        self.assertEqual(hits_before + 1, self.upstream.hits())


if __name__ == "__main__":
    unittest.main()
