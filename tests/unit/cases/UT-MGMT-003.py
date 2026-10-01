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
    def test_mutate_success_audited(self):
        self.admin.mutate("a","do","t","r",lambda conn:1);self.assertEqual(self.fx.app.audit.page()["data"][0]["result"],"success")
    def test_mutate_failure_audited(self):
        with self.assertRaises(ValueError):self.admin.mutate("a","do","t","r",lambda conn:(_ for _ in ()).throw(ValueError()))
        self.assertEqual(self.fx.app.audit.page()["data"][0]["result"],"failed")
    def test_mutate_is_atomic_with_registry_write(self):
        body={"name":"p","kind":"local","endpoint":"http://x","secret_ref":None,"enabled":True}
        with self.assertRaises(ValueError):
            self.admin.mutate("a","provider.create","provider","r",
                              lambda conn:(self.fx.app.registry.create_provider(body,conn=conn),(_ for _ in ()).throw(ValueError()))[1])
        self.assertEqual(self.fx.app.registry.list_providers(),[])


import unittest

from tests.common.fakes import AppFixture


class AuditTests(unittest.TestCase):
    def setUp(self):self.fx=AppFixture();self.audit=self.fx.app.audit
    def tearDown(self):self.fx.close()
    def test_record(self):
        before=len(self.audit.page()["data"])
        self.audit.record("a","x","t","ok")
        page=self.audit.page()["data"]
        self.assertEqual(len(page),before+1)
        self.assertEqual(page[0]["action"],"x")
        self.assertEqual(page[0]["actor"],"a")
    def test_actor(self):self.audit.record("alice","x","t","ok");self.assertEqual(self.audit.page()["data"][0]["actor"],"alice")
    def test_action(self):self.audit.record("a","change","t","ok");self.assertEqual(self.audit.page()["data"][0]["action"],"change")
    def test_target(self):self.audit.record("a","x","resource","ok");self.assertEqual(self.audit.page()["data"][0]["target"],"resource")
    def test_result(self):self.audit.record("a","x","t","failed");self.assertEqual(self.audit.page()["data"][0]["result"],"failed")
    def test_request_id_exposed(self):self.audit.record("a","x","t","ok","corr-1");self.assertEqual(self.audit.page()["data"][0]["request_id"],"corr-1")
    def test_limit(self):
        for i in range(3):self.audit.record("a",str(i),"t","ok")
        self.assertEqual(len(self.audit.page(2)["data"]),2)
