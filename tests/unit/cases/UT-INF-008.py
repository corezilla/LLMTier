from __future__ import annotations

import http.client
import io
import json
import tempfile
import unittest
import urllib.error
from email.message import Message
from pathlib import Path
from unittest.mock import patch

from http_api.errors import ApiError
from inference.providers.openai import OpenAIProvider


class FakeResponse:
    def __init__(self, body, content_type="application/json", status=200):
        self.body = body if isinstance(body, bytes) else body.encode()
        self.status = status
        self.headers = Message()
        self.headers["Content-Type"] = content_type

    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self): return self.body


class OpenAIProviderTests(unittest.TestCase):
    def test_probe_uses_authenticated_models_endpoint(self):
        with tempfile.TemporaryDirectory() as root:
            secret=Path(root)/"key"; secret.write_text("secret-value")
            seen={}
            def open_url(req, timeout, **kwargs):
                seen["url"],seen["auth"]=req.full_url,req.headers.get("Authorization")
                return FakeResponse(json.dumps({"object":"list","data":[]}))
            with patch("urllib.request.urlopen",side_effect=open_url):
                self.assertTrue(OpenAIProvider("https://provider.example",f"file:{secret}").probe())
            self.assertEqual(seen["url"],"https://provider.example/models")
            self.assertEqual(seen["auth"],"Bearer secret-value")




    def test_remote_disconnect_maps_to_provider_unavailable(self):
        # ST-EMB-010 transport branch: an upstream that drops the connection
        # without a response raises http.client.RemoteDisconnected, which is NOT
        # a urllib.error.URLError. It must still map to 503 provider_unavailable.
        with patch("urllib.request.urlopen",side_effect=http.client.RemoteDisconnected("remote closed")):
            with self.assertRaises(ApiError) as caught:
                OpenAIProvider("https://provider.example",None).embed("m",{"input":"x"})
        self.assertEqual((caught.exception.status,caught.exception.code,caught.exception.retryable),(503,"provider_unavailable",True))

    def test_url_error_maps_to_provider_unavailable(self):
        # E-INF-UPSTREAM: a URL/transport error (unreachable host) → 503.
        with patch("urllib.request.urlopen",side_effect=urllib.error.URLError("no route to host")):
            with self.assertRaises(ApiError) as caught:
                OpenAIProvider("https://provider.example",None).embed("m",{"input":"x"})
        self.assertEqual((caught.exception.status,caught.exception.code,caught.exception.retryable),(503,"provider_unavailable",True))

    def test_timeout_maps_to_provider_unavailable(self):
        # E-INF-UPSTREAM: a connect/read timeout → 503.
        with patch("urllib.request.urlopen",side_effect=TimeoutError("timed out")):
            with self.assertRaises(ApiError) as caught:
                OpenAIProvider("https://provider.example",None).embed("m",{"input":"x"})
        self.assertEqual((caught.exception.status,caught.exception.code,caught.exception.retryable),(503,"provider_unavailable",True))


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
