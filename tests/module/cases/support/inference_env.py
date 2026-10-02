"""Assembly helpers for MT-INF-* module cases.

Wires a *cloud* provider whose endpoint is a programmable loopback
`FakeUpstream` through the public Registry entries, so the assembled
`ResponsesService`/`EmbeddingsService` exercise the real `OpenAIProvider`
transport. For pure service-level cases the FakeAdapter boundary double
(`_test_adapter` seam, asset `llmtier-unit-fakes`) is used instead.
"""
from __future__ import annotations

import json
import unittest

from tests.common.fakes import AppFixture, embedding_capabilities, response_capabilities
from tests.module.cases.support.upstream import FakeUpstream

RESPONSE_BODY = {"model": "Senior", "input": "hi", "stream": True, "store": False}
EMBEDDING_BODY = {"model": "Embedding-v1", "input": "hi", "encoding_format": "float"}


class InferenceEnv(unittest.TestCase):
    def setUp(self):
        self.fx = AppFixture()
        self.upstream = FakeUpstream(mode="ok")
        self.senior = self._wire_cloud("Senior", response_capabilities())[1]
        self.embedding = self._wire_cloud("Embedding-v1", embedding_capabilities())[1]
        self.deployment = self.senior

    def tearDown(self):
        self.upstream.stop()
        self.fx.close()

    def _wire_cloud(self, tier, caps):
        provider, _ = self.fx.app.registry.create_provider(
            {"name": f"cloud-{tier}", "kind": "cloud", "endpoint": self.upstream.endpoint,
             "secret_ref": None, "enabled": True})
        deployment, _ = self.fx.app.registry.create_deployment(
            {"name": f"cloud-dep-{tier}", "provider_id": provider["id"], "backend_model": "backend",
             "capabilities": caps, "enabled": True})
        view, etag = self.fx.app.registry.get_service_level(tier)
        self.fx.app.registry.update_service_level(tier, {"deployment_ids": [deployment["id"]]}, etag)
        # 夹具播种（与 AppFixture.seed 同口径）：候选健康态置 healthy
        self.fx.app.store.connection().execute("UPDATE deployments SET health='healthy' WHERE id=?", (deployment["id"],))
        self.deployment = deployment
        return provider, deployment

    def set_timeouts(self, connect_ms=None, idle_ms=None, deployment_id=None):
        """Storage-face injection: shrink runtime profile timeouts (scheme §1.5.1 c1/c2)."""
        did = deployment_id or self.deployment["id"]
        conn = self.fx.app.store.connection()
        if connect_ms is not None:
            conn.execute("UPDATE deployment_runtime_profiles SET connect_timeout_ms=? WHERE deployment_id=?", (connect_ms, did))
        if idle_ms is not None:
            conn.execute("UPDATE deployment_runtime_profiles SET stream_idle_timeout_ms=? WHERE deployment_id=?", (idle_ms, did))

    def upstream_mode(self, mode, **kwargs):
        self.upstream.mode = mode
        for key, value in kwargs.items():
            setattr(self.upstream, key, value)

    def usage_rows(self):
        page = self.fx.app.usage.page("consumer", None, 200, admin=True,
                                       since="2000-01-01T00:00:00Z", until="2100-01-01T00:00:00Z")
        return page["data"]

    def head_record(self, principal="consumer", request_id=None):
        rows = self.usage_rows()
        if request_id:
            rows = [r for r in rows if r["request_id"] == request_id]
        return rows[-1] if rows else None
