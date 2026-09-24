import unittest

from http_api.errors import ApiError
from http_api.health import apply_probe_result, health_view, readiness_view
from .fakes import AppFixture


class HealthTests(unittest.TestCase):
    def setUp(self):self.fx=AppFixture()
    def tearDown(self):self.fx.close()
    def test_health_ok(self):self.assertEqual(health_view("x"),{"status":"ok","version":"x"})
    def test_empty_is_not_ready(self):self.assertEqual(readiness_view(self.fx.app.registry)[0]["status"],"not_ready")
    def test_one_model_is_degraded(self):self.fx.seed();self.assertEqual(readiness_view(self.fx.app.registry)[0]["status"],"degraded")
    def test_not_ready_http_status(self):self.assertEqual(readiness_view(self.fx.app.registry)[1],503)
    def test_probe_persists(self):
        _,d=self.fx.seed(health="unknown");apply_probe_result(self.fx.app.registry,d["id"],"healthy","r");self.assertEqual(self.fx.app.registry.get_deployment(d["id"])[0]["health"],"healthy")
    def test_probe_unknown_deployment(self):
        with self.assertRaises(ApiError):apply_probe_result(self.fx.app.registry,"none","healthy","r")
    def test_probe_invalid_status(self):
        with self.assertRaises(ApiError):apply_probe_result(self.fx.app.registry,"none","bad","r")
