"""MT-INF-002 — EmbeddingsService 组装后向量化契约（M003，层①，boundary，P0）。

组装保证：float/base64 两编码、usage→`prompt_tokens` 归一、`Embedding-v1`
冻结维数约束、非有限值/非法维数拒绝。base64 经本地替身返回冻结向量。
"""
from __future__ import annotations

import base64
import json
import math
import struct
import unittest

from inference.providers.base import ProviderResult
from tests.common.fakes import FakeAdapter
from tests.module.cases.support.inference_env import EMBEDDING_BODY, InferenceEnv


class _VectorAdapter(FakeAdapter):
    def __init__(self, vector, encoding="float"):
        super().__init__(usage=True)
        self.vector = vector
        self.encoding = encoding

    def embed(self, model, request):
        vector = self.vector
        if self.encoding == "base64":
            vector = base64.b64encode(struct.pack("<%df" % len(self.vector), *self.vector)).decode()
        return {"object": "list", "data": [{"object": "embedding", "index": 0, "embedding": vector}],
                "model": model, "usage": {"prompt_tokens": 7, "total_tokens": 7}}


class EmbeddingsContractTests(InferenceEnv):
    def _create(self, body=None, adapter=None):
        self.fx.app.embeddings._test_adapter = adapter
        try:
            return self.fx.app.embeddings.create("consumer", "req_embed_1", body or EMBEDDING_BODY)
        finally:
            self.fx.app.embeddings._test_adapter = None

    def test_float_encoding_roundtrip(self):
        result = self._create(adapter=_VectorAdapter([0.25, -0.5]))
        self.assertEqual([0.25, -0.5], result["data"][0]["embedding"])
        self.assertEqual("Embedding-v1", result["model"])

    def test_base64_encoding_decoded_and_validated(self):
        result = self._create(body={**EMBEDDING_BODY, "encoding_format": "base64"},
                              adapter=_VectorAdapter([1.0, 2.0], encoding="base64"))
        # 契约：base64 编码时返回值保留 base64 串，且服务端已解码校验（坏值会 502）
        self.assertEqual("AACAPwAAAEA=", result["data"][0]["embedding"])
        self.assertEqual([1.0, 2.0], list(struct.unpack("<2f", base64.b64decode(result["data"][0]["embedding"]))))

    def test_usage_normalizes_prompt_tokens(self):
        self._create(adapter=_VectorAdapter([0.5]))
        row = self.head_record()
        self.assertEqual((7, 0, 7), (row["input_tokens"], row["output_tokens"], row["total_tokens"]))
        self.assertEqual("measured", row["measurement_status"])

    def test_non_finite_vector_rejected_502(self):
        with self.assertRaises(Exception) as cm:
            self._create(adapter=_VectorAdapter([float("nan"), 1.0]))
        code = getattr(cm.exception, "code", None)
        self.assertEqual("provider_contract_error", code)
        row = self.head_record()
        self.assertEqual("unknown", row["measurement_status"])
        self.assertIsNone(row["input_tokens"])

    def test_frozen_dimensions_enforced(self):
        with self.assertRaises(Exception) as cm:
            self._create(body={**EMBEDDING_BODY, "dimensions": 512}, adapter=_VectorAdapter([0.5]))
        self.assertEqual("unsupported_dimensions", cm.exception.code)
        self.assertEqual(400, cm.exception.status)

    def test_non_finite_rejected_as_502_via_upstream(self):
        # 真实 transport：上游返回含非有限值的向量 → 502 provider_contract_error
        self.upstream_mode("badvector")
        with self.assertRaises(Exception) as cm:
            self.fx.app.embeddings.create("consumer", "req_embed_2", EMBEDDING_BODY)
        self.assertEqual("provider_contract_error", cm.exception.code)
        self.assertEqual(502, cm.exception.status)


if __name__ == "__main__":
    unittest.main()
