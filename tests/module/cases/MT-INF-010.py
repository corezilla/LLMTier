"""MT-INF-010 — Embeddings 分支矩阵（M003，层②，boundary，P0）。

分支：非法 base64→502 `provider_contract_error`；空向量/非有限值拒绝→502；
坏向量（transport 层注入）→502；usage 缺失→unknown 不补零。
替身经 `_test_adapter` seam 与本地 FakeUpstream（b6/b7 落点）。
"""
from __future__ import annotations

import unittest

from tests.common.fakes import FakeAdapter
from tests.module.cases.support.inference_env import EMBEDDING_BODY, InferenceEnv


class _RawVectorAdapter(FakeAdapter):
    def __init__(self, embedding, with_usage=True):
        super().__init__(usage=with_usage)
        self.embedding = embedding

    def embed(self, model, request):
        payload = {"object": "list", "data": [{"object": "embedding", "index": 0, "embedding": self.embedding}],
                   "model": model}
        if self.has_usage:
            payload["usage"] = {"prompt_tokens": 3, "total_tokens": 3}
        return payload


class EmbeddingBranchTests(InferenceEnv):
    def _create(self, adapter, body=None):
        self.fx.app.embeddings._test_adapter = adapter
        try:
            return self.fx.app.embeddings.create("consumer", "req_emb_branch", body or EMBEDDING_BODY)
        finally:
            self.fx.app.embeddings._test_adapter = None

    def test_invalid_base64_is_502_contract_error(self):
        with self.assertRaises(Exception) as cm:
            self._create(_RawVectorAdapter("!!!not-base64!!!"),
                         body={**EMBEDDING_BODY, "encoding_format": "base64"})
        self.assertEqual(("provider_contract_error", 502), (cm.exception.code, cm.exception.status))

    def test_empty_vector_rejected(self):
        with self.assertRaises(Exception) as cm:
            self._create(_RawVectorAdapter([]))
        self.assertEqual("provider_contract_error", cm.exception.code)

    def test_non_finite_values_rejected(self):
        for vector in ([float("inf"), 0.1], [float("nan")]):
            with self.assertRaises(Exception) as cm:
                self._create(_RawVectorAdapter(vector))
            self.assertEqual("provider_contract_error", cm.exception.code)

    def test_bad_base64_payload_from_transport_is_502(self):
        self.upstream_mode("embed_ok")
        # 上游返回合法 float 向量 + base64 请求 → 服务端按 base64 解码失败 → 502
        with self.assertRaises(Exception) as cm:
            self._create(None, body={**EMBEDDING_BODY, "encoding_format": "base64"})
        self.assertEqual("provider_contract_error", cm.exception.code)
        row = self.head_record("req_emb_branch")
        self.assertEqual("unknown", row["measurement_status"])

    def test_usage_missing_is_unknown_not_zero(self):
        result = self._create(_RawVectorAdapter([0.5], with_usage=False))
        self.assertEqual([0.5], result["data"][0]["embedding"])
        row = self.head_record("req_emb_branch")
        self.assertTrue(row["is_final"])
        self.assertIsNone(row["input_tokens"])
        self.assertEqual("unknown", row["measurement_status"])


if __name__ == "__main__":
    unittest.main()
