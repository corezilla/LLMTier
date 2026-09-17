from __future__ import annotations

import time

from .errors import ApiError
from .registry import Registry


class ModelCatalog:
    def __init__(self, registry: Registry):
        self.registry = registry

    def _view(self, level: dict) -> dict:
        candidates = self.registry.candidates(level["id"])
        health = [c.health for c in candidates]
        availability = "unavailable" if not candidates or all(h == "unhealthy" for h in health) else ("degraded" if any(h in {"degraded", "unhealthy", "unknown"} for h in health) else "available")
        return {"id": level["id"], "object": "model", "created": int(time.time()), "owned_by": "llmtier", "availability": availability, "capabilities": level["capabilities"]}

    def list(self) -> dict:
        return {"object": "list", "data": [self._view(level) for level in self.registry.list_service_levels()]}

    def get(self, model_id: str) -> dict:
        try:
            return self._view(self.registry.get_service_level(model_id)[0])
        except ApiError as exc:
            if exc.status == 404:
                raise ApiError(404, "model_not_found", "Model not found") from exc
            raise
