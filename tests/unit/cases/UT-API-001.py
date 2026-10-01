from __future__ import annotations

import unittest

from http_api.errors import ApiError, require


class ErrorTests(unittest.TestCase):
    def test_status(self):self.assertEqual(ApiError(400,"x","m").status,400)
    def test_client_type(self):self.assertEqual(ApiError(400,"x","m").envelope()["error"]["type"],"request_error")
    def test_server_type(self):self.assertEqual(ApiError(500,"x","m").envelope()["error"]["type"],"server_error")
    def test_code(self):self.assertEqual(ApiError(400,"code","m").envelope()["error"]["code"],"code")
    def test_param(self):self.assertEqual(ApiError(400,"x","m","field").envelope()["error"]["param"],"field")
    def test_require_true(self):self.assertIsNone(require(True,400,"x","m"))
    def test_require_false(self):
        with self.assertRaises(ApiError) as cm:require(False,422,"x","m")
        self.assertEqual(cm.exception.status,422)


import unittest

from http_api.errors import ApiError
from http_api.health import apply_probe_result, health_view, readiness_view
from tests.common.fakes import AppFixture


class HealthTests(unittest.TestCase):
    def setUp(self):self.fx=AppFixture()
    def tearDown(self):self.fx.close()
    def test_health_ok(self):self.assertEqual(health_view("x"),{"status":"ok","version":"x"})
