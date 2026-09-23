import json
import unittest

from llmtier_v03.errors import ApiError
from .fakes import AppFixture, FakeAdapter


def _stats_response(payload: dict) -> dict:
    return {"error": {"message": payload, "type": "server_error", "code": "provider_unavailable", "param": None, "retryable": True}}


class DiagnosticsSwitchTests(unittest.TestCase):
    def setUp(self):
        self.fx = AppFixture(); self.d = self.fx.app.diagnostics

    def tearDown(self): self.fx.close()

    def test_switches_default_off_and_runtime_toggle(self):
        self.assertEqual(self.d.switches(), {"snapshots_enabled": False, "stats_enabled": False})
        self.d.set_switches(snapshots_enabled=True, stats_enabled=True)
        self.assertEqual(self.d.switches(), {"snapshots_enabled": True, "stats_enabled": True})
        self.d.set_switches(snapshots_enabled=False)
        self.assertEqual(self.d.switches()["snapshots_enabled"], False)
        self.assertEqual(self.d.switches()["stats_enabled"], True)


class InjectionConfigTests(unittest.TestCase):
    def setUp(self):
        self.fx = AppFixture(); self.fx.seed(); self.d = self.fx.app.diagnostics; self.did = self.fx.app.registry.list_deployments()[0]["id"]

    def tearDown(self): self.fx.close()

    def test_unknown_type_rejected(self):
        with self.assertRaises(ApiError) as cm:
            self.d.set_injections(self.did, [{"type": "nope", "config": {}, "enabled": True}])
        self.assertEqual(cm.exception.code, "invalid_injection")

    def test_missing_or_out_of_range_config_rejected(self):
        with self.assertRaises(ApiError): self.d.set_injections(self.did, [{"type": "delay", "config": {}, "enabled": True}])
        with self.assertRaises(ApiError): self.d.set_injections(self.did, [{"type": "delay", "config": {"delay_ms": 60001}, "enabled": True}])
        with self.assertRaises(ApiError): self.d.set_injections(self.did, [{"type": "rate_limit", "config": {"retry_after_sec": -1}, "enabled": True}])
        with self.assertRaises(ApiError): self.d.set_injections(self.did, [{"type": "stream_terminate", "config": {"stream_terminate_after_events": 0}, "enabled": True}])

    def test_error_body_truncated_to_512_bytes(self):
        self.d.set_injections(self.did, [{"type": "fault_502", "config": {"error_body": "x" * 600}, "enabled": True}])
        items = self.d.injections(self.did)
        self.assertEqual(len(items[0]["config"]["error_body"].encode()), 512)

    def test_upsert_partial_update_keeps_other_types(self):
        self.d.set_injections(self.did, [
            {"type": "fault_502", "config": {"error_body": "a"}, "enabled": True},
            {"type": "delay", "config": {"delay_ms": 100}, "enabled": True},
        ])
        self.d.set_injections(self.did, [{"type": "delay", "config": {"delay_ms": 200}, "enabled": False}])
        items = {x["type"]: x for x in self.d.injections(self.did)}
        self.assertTrue(items["fault_502"]["enabled"])
        self.assertFalse(items["delay"]["enabled"])
        self.assertEqual(items["delay"]["config"]["delay_ms"], 200)

    def test_unknown_deployment_rejected(self):
        with self.assertRaises(ApiError): self.d.set_injections("dep_missing", [{"type": "delay", "config": {"delay_ms": 1}, "enabled": True}])


class InjectionEnforcementTests(unittest.TestCase):
    def setUp(self):
        self.fx = AppFixture(); self.fx.seed(); self.store = self.fx.app.store
        self.service = self.fx.app.responses
        self.service._adapter = lambda _: FakeAdapter()
        self.d = self.fx.app.diagnostics
        self.did = self.fx.app.registry.list_deployments()[0]["id"]
        self.body = {"model": "Worker", "input": "hello", "stream": True, "store": False}

    def tearDown(self): self.fx.close()

    def test_fault_502_returns_injected_error_and_marks_usage(self):
        self.d.set_injections(self.did, [{"type": "fault_502", "config": {"error_body": "injected backend error"}, "enabled": True}])
        with self.assertRaises(ApiError) as cm:
            self.service.create("p", "r-inj", self.body)
        self.assertEqual(cm.exception.status, 502)
        self.assertEqual(cm.exception.code, "provider_failure")
        self.assertIn("injected backend error", cm.exception.message)
        page = self.fx.app.usage.page("p", None, since="2000-01-01T00:00:00Z", until="2100-01-01T00:00:00Z")
        self.assertEqual(page["data"][0]["source"], "injected")

    def test_rate_limit_injection_returns_429_with_retry_after(self):
        self.d.set_injections(self.did, [{"type": "rate_limit", "config": {"retry_after_sec": 7}, "enabled": True}])
        with self.assertRaises(ApiError) as cm:
            self.service.create("p", "r-rl", self.body)
        self.assertEqual(cm.exception.status, 429)
        self.assertEqual(cm.exception.headers.get("Retry-After"), "7")

    def test_delay_injection_still_completes(self):
        self.d.set_injections(self.did, [{"type": "delay", "config": {"delay_ms": 10}, "enabled": True}])
        result = self.service.create("p", "r-delay", self.body)
        self.assertEqual(result["status"], "completed")
