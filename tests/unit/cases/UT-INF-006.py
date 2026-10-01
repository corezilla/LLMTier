import unittest

from http_api.errors import ApiError
from tests.common.fakes import AppFixture, FakeAdapter




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

    def test_unknown_field_is_400_unsupported_field(self):
        # System §7.8 ERR-REQ-FIELD (authority): unknown field -> unsupported_field,
        # param = offending field name.
        exc=self._code({**self.body,"bogus":1})
        self.assertEqual((exc.status,exc.code,exc.param),(400,"unsupported_field","bogus"))

    def test_forbidden_field_carries_param(self):
        exc=self._code({**self.body,"previous_response_id":"resp_old"})
        self.assertEqual((exc.status,exc.code,exc.param),(400,"unsupported_field","previous_response_id"))

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
        from tests.common.fakes import response_capabilities
        _,d=self.fx.seed("Junior")
        caps={**response_capabilities(),"tools":False}
        self.fx.app.registry.update_deployment(d["id"],{"capabilities":caps},self.fx.app.registry.get_deployment(d["id"])[1])
        exc=self._code({**self.body,"model":"Junior","tools":[{"type":"function","name":"f"}]})
        self.assertEqual((exc.status,exc.code,exc.param),(400,"unsupported_request","tools"))

    def test_unsupported_responses_capability_is_400_unsupported_model(self):
        from tests.common.fakes import embedding_capabilities
        self.fx.seed("Embedding-v1",embedding_capabilities(),"BAAI/bge-m3")
        exc=self._code({**self.body,"model":"Embedding-v1"})
        self.assertEqual((exc.status,exc.code,exc.param),(400,"unsupported_model","model"))



