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
    def test_first_page_snapshot_is_frozen(self):
        # The first page freezes the source set; later pages must serve the
        # frozen screen even if the live data changes in between.
        data=[{"id":str(i),"value":"original"} for i in range(3)]
        first=self.admin.page(data,"operator","frozen",limit=2)
        self.assertEqual([r["id"] for r in first["data"]],["0","1"])
        self.assertTrue(first["page"]["has_more"])
        data[2]["value"]="changed"
        data.append({"id":"9","value":"new"})
        second=self.admin.page(data,"operator","frozen",first["page"]["next_cursor"],limit=2)
        self.assertEqual([r["id"] for r in second["data"]],["2"])
        self.assertEqual(second["data"][0]["value"],"original")
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
