from __future__ import annotations

import json
import tempfile
from pathlib import Path

from llmtier_v03.app import Application
from llmtier_v03.providers.base import ProviderResult


def response_capabilities():
    return {"responses": True, "embeddings": False, "tools": True, "structured_outputs": False, "input_modalities": ["text"], "output_modalities": ["text"], "context_window": 128000, "max_output_tokens": 16384, "embedding_space_id": None, "embedding_dimensions": None, "embedding_max_batch_inputs": None, "embedding_max_input_tokens": None}


def embedding_capabilities():
    return {"responses": False, "embeddings": True, "tools": False, "structured_outputs": False, "input_modalities": ["text"], "output_modalities": ["embedding"], "context_window": None, "max_output_tokens": None, "embedding_space_id": "bge-m3-dense-1024-v1", "embedding_dimensions": [1024], "embedding_max_batch_inputs": 32, "embedding_max_input_tokens": 8192}


class AppFixture:
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory(); root = Path(self.temp.name)
        settings = root / "settings.json"; settings.write_text(json.dumps({"providers": [], "deployments": [], "service_levels": []}))
        self.app = Application(str(root / "state.sqlite3"), str(settings))

    def close(self):
        self.app.store.close(); self.temp.cleanup()

    def seed(self, tier="Worker", capabilities=None, backend_model="synthetic-chat", health="healthy"):
        capabilities = capabilities or response_capabilities()
        provider, _ = self.app.registry.create_provider({"name": f"provider-{tier}", "kind": "local", "endpoint": "http://127.0.0.1:9", "secret_ref": None, "enabled": True})
        deployment, _ = self.app.registry.create_deployment({"name": f"deployment-{tier}", "provider_id": provider["id"], "backend_model": backend_model, "capabilities": capabilities, "enabled": True})
        level, etag = self.app.registry.get_service_level(tier)
        self.app.registry.update_service_level(tier, {"deployment_ids": [deployment["id"]]}, etag)
        self.app.store.connection().execute("UPDATE deployments SET health=? WHERE id=?", (health, deployment["id"]))
        return provider, deployment


class FakeAdapter:
    def __init__(self, usage=True, refusal=False, fail=None): self.has_usage=usage; self.refusal=refusal; self.fail=fail
    def complete(self, model, request):
        if self.fail: raise self.fail
        content = {"type": "refusal", "refusal": "no"} if self.refusal else {"type": "output_text", "text": "ok", "annotations": []}
        usage = {"input_tokens": 2, "output_tokens": 1, "total_tokens": 3} if self.has_usage else None
        return ProviderResult([{"type": "message", "id": "msg_1", "role": "assistant", "status": "completed", "content": [content]}], usage)
    def embed(self, model, request):
        count = 1 if isinstance(request["input"], str) else len(request["input"]); dimension = request.get("dimensions", 1024)
        return {"object": "list", "data": [{"object": "embedding", "index": i, "embedding": [0.0] * dimension} for i in range(count)], "model": model, "usage": {"prompt_tokens": count, "total_tokens": count}}
    def probe(self): return True
