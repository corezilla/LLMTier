"""MT-INF-005 — 校验顺序四出口（M003，层②，negative，P0）。

按实现顺序分别断言：缺字段→`invalid_request`（param=首个缺失）；
stream/store 形态→`unsupported_request`；禁字段→`unsupported_field`；
未知字段→`unsupported_field`。`param` 指向违规字段。
"""
from __future__ import annotations

import unittest

from http_api.errors import ApiError
from tests.common.fakes import FakeAdapter
from tests.module.cases.support.inference_env import RESPONSE_BODY, InferenceEnv


class ValidationOrderTests(InferenceEnv):
    def _create(self, body):
        self.fx.app.responses._test_adapter = FakeAdapter()
        try:
            return self.fx.app.responses.create("consumer", "req_val", body)
        finally:
            self.fx.app.responses._test_adapter = None

    def test_missing_field_is_invalid_request_with_param(self):
        for removed, param in (("model", "model"), ("input", "input"), ("stream", "stream"), ("store", "store")):
            body = {k: v for k, v in RESPONSE_BODY.items() if k != removed}
            with self.assertRaises(ApiError) as cm:
                self._create(body)
            self.assertEqual(("invalid_request", 400, param), (cm.exception.code, cm.exception.status, cm.exception.param))

    def test_wrong_stream_store_shape_is_unsupported_request(self):
        for body in ({**RESPONSE_BODY, "stream": False}, {**RESPONSE_BODY, "store": True},
                     {**RESPONSE_BODY, "stream": False, "store": True}):
            with self.assertRaises(ApiError) as cm:
                self._create(body)
            self.assertEqual(("unsupported_request", 400), (cm.exception.code, cm.exception.status))

    def test_forbidden_field_beats_unknown_field(self):
        with self.assertRaises(ApiError) as cm:
            self._create({**RESPONSE_BODY, "prompt_cache_key": "x", "mystery": 1})
        self.assertEqual(("unsupported_field", "prompt_cache_key"), (cm.exception.code, cm.exception.param))

    def test_unknown_field_is_unsupported_field(self):
        with self.assertRaises(ApiError) as cm:
            self._create({**RESPONSE_BODY, "mystery": 1})
        self.assertEqual(("unsupported_field", "mystery"), (cm.exception.code, cm.exception.param))
        self.assertEqual(400, cm.exception.status)


if __name__ == "__main__":
    unittest.main()
