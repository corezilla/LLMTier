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


class ResponsesValidationGapTests(unittest.TestCase):
    """UT-INF-001/006: validation order, codes, and capability gates."""

    def setUp(self):
        self.fx=AppFixture(); self.fx.seed("Worker"); self.service=self.fx.app.responses; self.service._adapter=lambda _:FakeAdapter()
        self.body={"model":"Worker","input":"hello","stream":True,"store":False}
    def tearDown(self): self.fx.close()

    def _code(self,body):
        with self.assertRaises(ApiError) as cm: self.service.create("p","rx",body)
        return cm.exception

    def test_unknown_model_is_404_model_not_found(self):
        exc=self._code({**self.body,"model":"Nope"})
        self.assertEqual((exc.status,exc.code),(404,"model_not_found"))

    def test_unknown_field_is_400_invalid_request(self):
        exc=self._code({**self.body,"bogus":1})
        self.assertEqual((exc.status,exc.code),(400,"invalid_request"))

    def test_max_output_tokens_zero_is_400(self):
        exc=self._code({**self.body,"max_output_tokens":0})
        self.assertEqual((exc.status,exc.code,exc.param),(400,"invalid_request","max_output_tokens"))

    def test_max_output_tokens_non_integer_bool_is_400(self):
        exc=self._code({**self.body,"max_output_tokens":True})
        self.assertEqual((exc.status,exc.code),(400,"invalid_request"))

    def test_max_output_tokens_over_capability_is_400(self):
        exc=self._code({**self.body,"max_output_tokens":10_000_000})
        self.assertEqual((exc.status,exc.code),(400,"invalid_request"))

    def test_max_output_tokens_within_range_accepted(self):
        self.assertEqual(self.service.create("p","ok-mot",{**self.body,"max_output_tokens":16})["status"],"completed")

    def test_tools_without_capability_is_400_unsupported_request(self):
        from .fakes import response_capabilities
        _,d=self.fx.seed("Junior")
        caps={**response_capabilities(),"tools":False}
        self.fx.app.registry.update_deployment(d["id"],{"capabilities":caps},self.fx.app.registry.get_deployment(d["id"])[1])
        exc=self._code({**self.body,"model":"Junior","tools":[{"type":"function","name":"f"}]})
        self.assertEqual((exc.status,exc.code,exc.param),(400,"unsupported_request","tools"))

    def test_unsupported_responses_capability_is_400_unsupported_model(self):
        from .fakes import embedding_capabilities
        self.fx.seed("Embedding-v1",embedding_capabilities(),"BAAI/bge-m3")
        exc=self._code({**self.body,"model":"Embedding-v1"})
        self.assertEqual((exc.status,exc.code,exc.param),(400,"unsupported_model","model"))

    def test_usage_non_integer_partial_is_unknown_with_nulls(self):
        class PartialAdapter(FakeAdapter):
            def complete(self,model,request):
                return type("R",(),{"output":[{"type":"message","id":"m","role":"assistant","status":"completed","content":[]}],"usage":{"input_tokens":"2","output_tokens":1,"total_tokens":3},"provider_request_id":None,"status":"completed","error":None,"incomplete_details":None})()
        self.service._adapter=lambda _:PartialAdapter()
        self.service.create("p","r-partial",self.body)
        row=self.fx.app.store.one("SELECT measurement_status,input_tokens,output_tokens,total_tokens FROM usage_record_versions WHERE request_id='r-partial' AND record_version=2")
        self.assertEqual(row["measurement_status"],"unknown")
        self.assertIsNone(row["input_tokens"]); self.assertIsNone(row["total_tokens"])

    def test_empty_provider_request_id_is_noop_via_service(self):
        self.service.create("p","r-empty-prid",self.body)
        row=self.fx.app.store.one("SELECT provider_request_id FROM provider_request_bindings WHERE principal_id='p' AND request_id='r-empty-prid'")
        self.assertIsNone(row["provider_request_id"])

    def test_injected_source_recorded_on_injected_fault(self):
        _,d=self.fx.seed("Senior")
        self.fx.app.diagnostics.set_injections(d["id"],[{"type":"fault_502","config":{"error_body":"boom"},"enabled":True}])
        body={**self.body,"model":"Senior"}
        with self.assertRaises(ApiError): self.service.create("p","r-inj",body)
        page=self.fx.app.usage.page("p",None,since="2000-01-01T00:00:00Z",until="2100-01-01T00:00:00Z")
        self.assertEqual(page["data"][0]["source"],"injected")
