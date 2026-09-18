from __future__ import annotations

import base64
import math
import struct
import uuid
from typing import Any

from .errors import ApiError, require
from .providers.local import LocalProvider
from .providers.openai import OpenAIProvider
from .registry import Registry
from .routing import Router
from .usage import UsageRecorder


class EmbeddingsService:
    def __init__(self, registry: Registry, router: Router, usage: UsageRecorder): self.registry, self.router, self.usage = registry, router, usage

    def _adapter(self, candidate):
        row = self.registry.store.one("SELECT secret_ref FROM providers WHERE id=?", (candidate.provider_id,))
        return (LocalProvider if candidate.kind == "local" else OpenAIProvider)(candidate.endpoint, row["secret_ref"] if row else None)

    def create(self, principal: str, request_id: str, body: dict[str, Any]) -> dict[str, Any]:
        require(set(body) <= {"model", "input", "encoding_format", "dimensions", "user"} and {"model", "input"} <= set(body), 400, "invalid_request", "Invalid embedding request")
        model, encoding = body["model"], body.get("encoding_format", "float")
        caps = self.registry.get_service_level(model)[0]["capabilities"]
        require(caps.get("embeddings") is True, 400, "unsupported_model", "Selected model does not support embeddings", "model")
        if body.get("dimensions") is not None and caps.get("embedding_dimensions"):
            require(body["dimensions"] in caps["embedding_dimensions"], 400, "unsupported_dimensions", "Unsupported embedding dimensions", "dimensions")
        self.usage.authorize_dispatch(principal, request_id, model, "/v1/embeddings")
        try:
            with self.router.admit(model) as candidate:
                self.usage.bind_backend(principal, request_id, candidate.provider_id, candidate.deployment_id)
                result = self._adapter(candidate).embed(candidate.backend_model, body)
            for item in result["data"]:
                vector = item.get("embedding")
                if encoding == "base64":
                    try:
                        raw = base64.b64decode(vector, validate=True)
                        values = struct.unpack("<" + "f" * (len(raw) // 4), raw)
                    except Exception as exc: raise ApiError(502, "provider_contract_error", "Invalid base64 embedding") from exc
                else: values = vector
                if not isinstance(values, (list, tuple)) or not values or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in values):
                    raise ApiError(502, "provider_contract_error", "Invalid embedding vector")
            embedding_usage = result.get("usage")
            normalized_usage = None
            if isinstance(embedding_usage, dict) and isinstance(embedding_usage.get("prompt_tokens"), int) and isinstance(embedding_usage.get("total_tokens"), int):
                normalized_usage = {"input_tokens": embedding_usage["prompt_tokens"], "output_tokens": 0, "total_tokens": embedding_usage["total_tokens"]}
            self.usage.finish(principal, request_id, normalized_usage)
            result["model"] = model
            return result
        except Exception:
            self.usage.finish(principal, request_id, None)
            raise
