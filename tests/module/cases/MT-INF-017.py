"""MT-INF-017 — 畸形帧与非 SS 帧（M003，层②，negative，P0；§1.5.1 b4/b5/c7）。

Oracle ＝ `src/`（方案 §1.5.1 规则；与矩阵预期 502 的偏差已在方案 §4 具名）：
- 非 `text/event-stream` Content-Type → 502 `provider_contract_error`（b5）
- 非 JSON `data:` 帧 → **503** `provider_unavailable`（src 实测，见 §4 G-INF-NONJSON-1）
- embeddings 非 JSON body → **503** `provider_unavailable`（b4，同上）
不伪装成功（无伪 terminal、无 measured 账本）。
"""
from __future__ import annotations

import unittest

from http_api.errors import ApiError
from tests.module.cases.support.inference_env import EMBEDDING_BODY, RESPONSE_BODY, InferenceEnv


class MalformedFrameTests(InferenceEnv):
    def test_non_sse_content_type_is_502(self):
        self.upstream_mode("non_sse")
        with self.assertRaises(ApiError) as cm:
            self.fx.app.responses.create("consumer", "req_nonsse", RESPONSE_BODY)
        self.assertEqual(("provider_contract_error", 502), (cm.exception.code, cm.exception.status))

    def test_non_json_data_frame_maps_503_per_src(self):
        # 设计-vs-实现偏差：矩阵 a25/c7 预期 502，src 实际 503 provider_unavailable
        self.upstream_mode("badframe")
        with self.assertRaises(ApiError) as cm:
            self.fx.app.responses.create("consumer", "req_badframe", RESPONSE_BODY)
        self.assertEqual(("provider_unavailable", 503), (cm.exception.code, cm.exception.status))
        self.assertTrue(cm.exception.retryable)

    def test_non_json_embeddings_body_maps_503_per_src(self):
        self.upstream_mode("nonjson")
        with self.assertRaises(ApiError) as cm:
            self.fx.app.embeddings.create("consumer", "req_emb_nonjson", EMBEDDING_BODY)
        self.assertEqual(("provider_unavailable", 503), (cm.exception.code, cm.exception.status))

    def test_malformed_stream_never_fakes_success(self):
        self.upstream_mode("badframe")
        with self.assertRaises(ApiError):
            self.fx.app.responses.create("consumer", "req_badframe2", RESPONSE_BODY)
        row = self.head_record("req_badframe2")
        self.assertEqual("unknown", row["measurement_status"])
        self.assertNotEqual("measured", row["measurement_status"])
        self.assertIsNone(row["total_tokens"])


if __name__ == "__main__":
    unittest.main()
