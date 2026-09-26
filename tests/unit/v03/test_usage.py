import unittest

from http_api.errors import ApiError
from .fakes import AppFixture


START="2000-01-01T00:00:00Z";END="2100-01-01T00:00:00Z"


class UsageTests(unittest.TestCase):
    def setUp(self):self.fx=AppFixture();self.u=self.fx.app.usage
    def tearDown(self):self.fx.close()
    def record(self,rid="r1",usage=None):self.u.authorize_dispatch("p",rid,"Worker","/v1/responses");self.u.finish("p",rid,usage)
    def test_unknown_created_before_finish(self):
        self.u.authorize_dispatch("p","r","Worker","/v1/responses");self.assertEqual(self.u.page("p",None,since=START,until=END)["data"][0]["measurement_status"],"unknown")
    def test_measured_replaces_head(self):
        self.record(usage={"input_tokens":2,"output_tokens":3,"total_tokens":5});self.assertEqual(self.u.page("p",None,since=START,until=END)["data"][0]["record_version"],2)
    def test_versions_are_immutable(self):
        self.record(usage={"input_tokens":2,"output_tokens":3,"total_tokens":5});self.assertEqual(self.fx.app.store.one("SELECT count(*) FROM usage_record_versions")[0],2)
    def test_unknown_values_are_null(self):
        self.record();r=self.u.page("p",None,since=START,until=END)["data"][0];self.assertIsNone(r["total_tokens"])
    def test_principal_scope(self):
        self.record();self.assertEqual(self.u.page("other",None,since=START,until=END)["data"],[])
    def test_admin_sees_all(self):
        self.record();self.assertEqual(len(self.u.page("admin",None,admin=True,since=START,until=END)["data"]),1)
    def test_snapshot_is_stable(self):
        self.record("r1",{"input_tokens":1,"output_tokens":1,"total_tokens":2});page=self.u.page("p",None,limit=1,since=START,until=END);self.record("r2",{"input_tokens":1,"output_tokens":1,"total_tokens":2});old=self.u.page("p",page["snapshot_id"]+":0",limit=10,since=START,until=END);self.assertEqual(len(old["data"]),1)
    def test_cursor_filter_mismatch(self):
        self.record();page=self.u.page("p",None,since=START,until=END)
        with self.assertRaises(ApiError):self.u.page("p",page["snapshot_id"]+":0",since="2001-01-01T00:00:00Z",until=END)
    def test_invalid_window(self):
        with self.assertRaises(ApiError):self.u.page("p",None,since=END,until=START)
    def test_record_provider_request_id_updates_binding(self):
        provider,deployment=self.fx.seed();self.u.authorize_dispatch("p","r","Worker","/v1/responses");self.u.bind_backend("p","r",provider["id"],deployment["id"]);self.u.record_provider_request_id("p","r","up-1");self.assertEqual(self.fx.app.store.one("SELECT provider_request_id FROM provider_request_bindings WHERE principal_id='p' AND request_id='r'")[0],"up-1")
    def test_record_provider_request_id_null_is_noop(self):
        provider,deployment=self.fx.seed();self.u.authorize_dispatch("p","r","Worker","/v1/responses");self.u.bind_backend("p","r",provider["id"],deployment["id"]);self.u.record_provider_request_id("p","r",None);self.assertIsNone(self.fx.app.store.one("SELECT provider_request_id FROM provider_request_bindings WHERE principal_id='p' AND request_id='r'")[0])
