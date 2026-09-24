import base64
import struct
import unittest

from http_api.errors import ApiError
from .fakes import AppFixture, FakeAdapter, embedding_capabilities


class Base64Adapter(FakeAdapter):
    def embed(self,model,request):
        raw=struct.pack("<"+"f"*1024,*([0.0]*1024));return {"object":"list","data":[{"object":"embedding","index":0,"embedding":base64.b64encode(raw).decode()}],"model":model,"usage":{"prompt_tokens":1,"total_tokens":1}}


class BadAdapter(FakeAdapter):
    def embed(self,model,request):return {"object":"list","data":[{"object":"embedding","index":0,"embedding":[float('nan')]}],"model":model,"usage":None}


class EmbeddingsTests(unittest.TestCase):
    def setUp(self):
        self.fx=AppFixture();self.fx.seed("Embedding-v1",embedding_capabilities(),"BAAI/bge-m3");self.service=self.fx.app.embeddings;self.service._adapter=lambda _:FakeAdapter();self.body={"model":"Embedding-v1","input":"a","dimensions":1024,"encoding_format":"float"}
    def tearDown(self):self.fx.close()
    def test_float_success(self):self.assertEqual(len(self.service.create("p","e1",self.body)["data"][0]["embedding"]),1024)
    def test_batch_count(self):
        body=dict(self.body,input=["a","b"]);self.assertEqual(len(self.service.create("p","e2",body)["data"]),2)
    def test_logical_model_returned(self):self.assertEqual(self.service.create("p","e3",self.body)["model"],"Embedding-v1")
    def test_base64_success(self):
        self.service._adapter=lambda _:Base64Adapter();body=dict(self.body,encoding_format="base64");self.assertIsInstance(self.service.create("p","e4",body)["data"][0]["embedding"],str)
    def test_wrong_dimension_rejected(self):
        with self.assertRaises(ApiError):self.service.create("p","e5",dict(self.body,dimensions=8))
    def test_unknown_field_rejected(self):
        with self.assertRaises(ApiError):self.service.create("p","e6",dict(self.body,extra=True))
    def test_nonfinite_rejected(self):
        self.service._adapter=lambda _:BadAdapter()
        with self.assertRaises(ApiError):self.service.create("p","e7",self.body)
    def test_usage_normalized(self):
        self.service.create("p","e8",self.body);page=self.fx.app.usage.page("p",None,since="2000-01-01T00:00:00Z",until="2100-01-01T00:00:00Z");self.assertEqual(page["data"][0]["input_tokens"],1)
