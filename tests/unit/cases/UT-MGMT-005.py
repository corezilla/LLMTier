from __future__ import annotations

import unittest
from unittest.mock import patch

from http_api.errors import ApiError
from tests.common.fakes import AppFixture


class ProbeAdapter:
    def __init__(self,*_):pass
    def probe(self):return True


class AdminTests(unittest.TestCase):
    def setUp(self):self.fx=AppFixture();self.admin=self.fx.app.admin
    def tearDown(self):self.fx.close()
    def test_probe_requires_confirmation(self):
        # A REAL existing deployment: the guard must be the thing that rejects,
        # not a downstream `not_found` from an unknown deployment id. Assert the
        # exact error and that no probe side effect (health write) happened.
        _,d=self.fx.seed(health="unknown")
        with self.assertRaises(ApiError) as cm:
            self.admin.probe("a",{"deployment_id":d["id"],"confirm_external_call":False},"r")
        self.assertEqual((cm.exception.status,cm.exception.code),(400,"confirmation_required"))
        self.assertEqual(self.fx.app.registry.get_deployment(d["id"])[0]["health"],"unknown")
        self.assertEqual([r for r in self.fx.app.audit.page()["data"] if r["action"]=="deployment.probe"],[])
    def test_probe_updates_health(self):
        _,d=self.fx.seed()
        with patch("management.admin.LocalProvider",ProbeAdapter):result=self.admin.probe("a",{"deployment_id":d["id"],"confirm_external_call":True},"r")
        self.assertEqual(result["status"],"healthy")


import unittest

from http_api.errors import ApiError
from http_api.health import apply_probe_result, health_view, readiness_view
from tests.common.fakes import AppFixture


class HealthTests(unittest.TestCase):
    def setUp(self):self.fx=AppFixture()
    def tearDown(self):self.fx.close()
    def test_probe_unknown_deployment(self):
        with self.assertRaises(ApiError):apply_probe_result(self.fx.app.registry,"none","healthy","r")
    def test_probe_invalid_status(self):
        with self.assertRaises(ApiError):apply_probe_result(self.fx.app.registry,"none","bad","r")
