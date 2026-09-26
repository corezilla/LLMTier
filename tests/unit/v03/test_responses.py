import unittest

from http_api.errors import ApiError
from .fakes import AppFixture, FakeAdapter


class ResponsesTests(unittest.TestCase):
    def setUp(self):
        self.fx=AppFixture(); self.fx.seed(); self.service=self.fx.app.responses; self.service._adapter=lambda _:FakeAdapter(); self.body={"model":"Worker","input":"hello","stream":True,"store":False}
    def tearDown(self): self.fx.close()
    def test_success(self): self.assertEqual(self.service.create("p","r1",self.body)["status"],"completed")
    def test_model_is_logical_id(self): self.assertEqual(self.service.create("p","r2",self.body)["model"],"Worker")
    def test_usage_is_preserved(self): self.assertEqual(self.service.create("p","r3",self.body)["usage"]["total_tokens"],3)
    def test_provider_request_id_is_persisted(self):
        self.service._adapter=lambda _:FakeAdapter(provider_request_id="up_req_123")
        self.service.create("p","r-prid",self.body)
        row=self.fx.app.store.one("SELECT provider_request_id FROM provider_request_bindings WHERE principal_id=? AND request_id=?",("p","r-prid"))
        self.assertEqual(row["provider_request_id"],"up_req_123")
    def test_missing_provider_request_id_stays_null(self):
        self.service.create("p","r-noprid",self.body)
        row=self.fx.app.store.one("SELECT provider_request_id FROM provider_request_bindings WHERE principal_id=? AND request_id=?",("p","r-noprid"))
        self.assertIsNone(row["provider_request_id"])
    def test_incomplete_status_is_preserved(self):
        self.service._adapter=lambda _:FakeAdapter(status="incomplete")
        value=self.service.create("p","r-incomplete",self.body)
        self.assertEqual(value["status"],"incomplete")
        self.assertEqual(value["incomplete_details"],{"reason":"max_output_tokens"})
    def test_missing_required_rejected(self):
        with self.assertRaises(ApiError):self.service.create("p","r4",{"model":"Worker"})
    def test_nonstream_rejected(self):
        body=dict(self.body,stream=False)
        with self.assertRaises(ApiError):self.service.create("p","r5",body)
    def test_store_true_rejected(self):
        body=dict(self.body,store=True)
        with self.assertRaises(ApiError):self.service.create("p","r6",body)
    def test_provider_continuation_rejected(self):
        body=dict(self.body,previous_response_id="resp_old")
        with self.assertRaises(ApiError) as cm:self.service.create("p","r7",body)
        self.assertEqual(cm.exception.code,"unsupported_field")
    def test_provider_failure_leaves_unknown_usage(self):
        self.service._adapter=lambda _:FakeAdapter(fail=ApiError(503,"provider_unavailable","x"))
        with self.assertRaises(ApiError):self.service.create("p","r8",self.body)
        page=self.fx.app.usage.page("p",None,since="2000-01-01T00:00:00Z",until="2100-01-01T00:00:00Z");self.assertEqual(page["data"][0]["measurement_status"],"unknown")
