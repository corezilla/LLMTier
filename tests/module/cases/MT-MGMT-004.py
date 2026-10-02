"""MT-MGMT-004 — Admin.probe 组装后探测（M004，层①，normal，P1）。

未确认→400 `confirmation_required`；loopback 假上游探测→healthy 落库；
不可达→unhealthy 落库；`may_have_incurred_cost`＝false。
"""
from __future__ import annotations

import unittest

from tests.module.cases.support.http_env import LoopbackEnv
from tests.module.cases.support.upstream import FakeUpstream


class ProbeTests(LoopbackEnv):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.upstream = FakeUpstream(mode="ok")

    @classmethod
    def tearDownClass(cls):
        cls.upstream.stop()
        super().tearDownClass()

    def _wire(self, name, endpoint):
        status, provider, _ = self.request("POST", "/v1/providers",
                                           body={"name": name, "kind": "local", "endpoint": endpoint,
                                                 "secret_ref": None, "enabled": True})
        self.assertEqual(201, status)
        caps = {"responses": True, "embeddings": False, "tools": True, "structured_outputs": False,
                "input_modalities": ["text"], "output_modalities": ["text"], "context_window": 128000,
                "max_output_tokens": 16384, "embedding_space_id": None, "embedding_dimensions": None,
                "embedding_max_batch_inputs": None, "embedding_max_input_tokens": None}
        status, deployment, _ = self.request("POST", "/v1/deployments",
                                             body={"name": f"{name}-dep", "provider_id": provider["id"],
                                                   "backend_model": "m", "capabilities": caps, "enabled": True})
        self.assertEqual(201, status)
        return provider, deployment

    def _probe(self, deployment_id, confirm=True):
        body = {"deployment_id": deployment_id}
        if confirm:
            body["confirm_external_call"] = True
        return self.request("POST", "/v1/probes", body=body)

    def test_unconfirmed_probe_is_400_confirmation_required(self):
        _, deployment = self._wire("probe-unconf", "http://127.0.0.1:9")
        status, payload, _ = self._probe(deployment["id"], confirm=False)
        self.assertEqual(400, status)
        self.assertEqual("confirmation_required", payload["error"]["code"])

    def test_probe_extra_field_is_400(self):
        _, deployment = self._wire("probe-extra", "http://127.0.0.1:9")
        status, payload, _ = self.request("POST", "/v1/probes",
                                          body={"deployment_id": deployment["id"], "confirm_external_call": True, "extra": 1})
        self.assertEqual(400, status)
        self.assertEqual("confirmation_required", payload["error"]["code"])

    def test_reachable_upstream_probe_is_healthy_persisted(self):
        _, deployment = self._wire("probe-ok", self.upstream.endpoint)
        status, payload, _ = self._probe(deployment["id"])
        self.assertEqual(200, status)
        self.assertEqual("healthy", payload["status"])
        self.assertFalse(payload["may_have_incurred_cost"])
        _, view, _ = self.request("GET", f"/v1/deployments/{deployment['id']}")
        self.assertEqual("healthy", view["health"])

    def test_unreachable_probe_is_unhealthy_persisted(self):
        _, deployment = self._wire("probe-down", "http://127.0.0.1:9")
        status, payload, _ = self._probe(deployment["id"])
        self.assertEqual(200, status)
        self.assertEqual("unhealthy", payload["status"])
        _, view, _ = self.request("GET", f"/v1/deployments/{deployment['id']}")
        self.assertEqual("unhealthy", view["health"])

    def test_probe_unknown_deployment_is_404(self):
        status, payload, _ = self._probe("dep_missing")
        self.assertEqual(404, status)


if __name__ == "__main__":
    unittest.main()
