import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from http_api.app import handler_factory
from http_api.errors import ApiError
from tests.common.fakes import AppFixture, FakeAdapter


def _stats_response(payload: dict) -> dict:
    return {"error": {"message": payload, "type": "server_error", "code": "provider_unavailable", "param": None, "retryable": True}}




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








class InjectionEnabledContractTests(unittest.TestCase):
    """InjectionWrite.enabled must be a real boolean (openapi: type boolean)."""

    def setUp(self):
        self.fx = AppFixture(); self.fx.seed(); self.d = self.fx.app.diagnostics; self.did = self.fx.app.registry.list_deployments()[0]["id"]

    def tearDown(self): self.fx.close()

    def test_non_boolean_enabled_rejected(self):
        for value in ("false", 1, 0, None, "true"):
            with self.assertRaises(ApiError) as cm:
                self.d.set_injections(self.did, [{"type": "delay", "config": {"delay_ms": 1}, "enabled": value}])
            self.assertEqual(cm.exception.code, "invalid_injection")

    def test_missing_enabled_rejected(self):
        with self.assertRaises(ApiError) as cm:
            self.d.set_injections(self.did, [{"type": "delay", "config": {"delay_ms": 1}}])
        self.assertEqual(cm.exception.code, "invalid_injection")

    def test_boolean_enabled_still_accepted(self):
        self.d.set_injections(self.did, [{"type": "delay", "config": {"delay_ms": 1}, "enabled": False}])
        self.assertFalse(self.d.injections(self.did)[0]["enabled"])
        self.d.set_injections(self.did, [{"type": "delay", "config": {"delay_ms": 1}, "enabled": True}])
        self.assertTrue(self.d.injections(self.did)[0]["enabled"])




