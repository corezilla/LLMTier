from __future__ import annotations

import time
import uuid
from typing import Any

from .errors import ApiError, require
from .providers.local import LocalProvider
from .providers.openai import OpenAIProvider
from .registry import Registry
from .routing import Router
from .usage import UsageRecorder


class ResponsesService:
    def __init__(self, registry: Registry, router: Router, usage: UsageRecorder):
        self.registry, self.router, self.usage = registry, router, usage

    def _adapter(self, candidate):
        row = self.registry.store.one("SELECT secret_ref FROM providers WHERE id=?", (candidate.provider_id,))
        cls = LocalProvider if candidate.kind == "local" else OpenAIProvider
        return cls(candidate.endpoint, row["secret_ref"] if row else None)

    def create(self, principal: str, request_id: str, body: dict[str, Any]) -> dict[str, Any]:
        required = {"model", "input", "stream", "store"}
        require(required <= set(body), 400, "invalid_request", "model, input, stream, and store are required")
        require(body.get("stream") is True and body.get("store") is False, 400, "unsupported_request", "Only stream=true and store=false are supported")
        forbidden = {"prompt_cache_key", "prompt_cache_retention", "previous_response_id"}
        require(not (forbidden & set(body)), 400, "unsupported_field", "Unsupported provider continuation or cache field")
        model = body["model"]
        caps = self.registry.get_service_level(model)[0]["capabilities"]
        require(caps.get("responses") is True, 400, "unsupported_model", "Selected model does not support Responses", "model")
        self.usage.authorize_dispatch(principal, request_id, model, "/v1/responses")
        try:
            with self.router.admit(model) as candidate:
                self.usage.bind_backend(principal, request_id, candidate.provider_id, candidate.deployment_id)
                result = self._adapter(candidate).complete(candidate.backend_model, body)
            self.usage.finish(principal, request_id, result.usage)
            return {
                "id": f"resp_{uuid.uuid4().hex}",
                "object": "response",
                "created_at": int(time.time()),
                "status": result.status,
                "model": model,
                "output": result.output,
                "usage": result.usage,
                "error": result.error,
                "incomplete_details": result.incomplete_details,
            }
        except Exception:
            self.usage.finish(principal, request_id, None)
            raise
