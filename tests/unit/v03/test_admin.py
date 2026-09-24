import unittest
from unittest.mock import patch

from http_api.errors import ApiError
from .fakes import AppFixture


class ProbeAdapter:
    def __init__(self,*_):pass
    def probe(self):return True


class AdminTests(unittest.TestCase):
    def setUp(self):self.fx=AppFixture();self.admin=self.fx.app.admin
    def tearDown(self):self.fx.close()
    def test_page_shape(self):
        page=self.admin.page([{"id":"a"}],"operator","x");self.assertEqual(page["data"],[{"id":"a"}])
    def test_page_limit(self):
        page=self.admin.page([{"id":str(i)} for i in range(3)],"operator","x",limit=2);self.assertTrue(page["page"]["has_more"])
    def test_page_cursor(self):
        first=self.admin.page([{"id":str(i)} for i in range(3)],"operator","x",limit=2);second=self.admin.page([],"operator","x",first["page"]["next_cursor"],2);self.assertEqual(second["data"][0]["id"],"2")
    def test_cursor_principal_bound(self):
        first=self.admin.page([{"id":"1"},{"id":"2"}],"a","x",limit=1)
        with self.assertRaises(ApiError):self.admin.page([],"b","x",first["page"]["next_cursor"],limit=1)
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
    def test_probe_requires_confirmation(self):
        with self.assertRaises(ApiError):self.admin.probe("a",{"deployment_id":"x","confirm_external_call":False},"r")
    def test_probe_updates_health(self):
        _,d=self.fx.seed()
        with patch("management.admin.LocalProvider",ProbeAdapter):result=self.admin.probe("a",{"deployment_id":d["id"],"confirm_external_call":True},"r")
        self.assertEqual(result["status"],"healthy")
