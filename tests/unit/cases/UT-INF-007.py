import base64
import struct
import unittest

from http_api.errors import ApiError
from tests.common.fakes import AppFixture, FakeAdapter, embedding_capabilities


class Base64Adapter(FakeAdapter):
    def embed(self,model,request):
        raw=struct.pack("<"+"f"*1024,*([0.0]*1024));return {"object":"list","data":[{"object":"embedding","index":0,"embedding":base64.b64encode(raw).decode()}],"model":model,"usage":{"prompt_tokens":1,"total_tokens":1}}


class BadAdapter(FakeAdapter):
    def embed(self,model,request):return {"object":"list","data":[{"object":"embedding","index":0,"embedding":[float('nan')]}],"model":model,"usage":None}




class EmbeddingsFailureGapTests(unittest.TestCase):
    """UT-INF-007: invalid base64 / empty vector / unsupported_dimensions codes."""

    def setUp(self):
        self.fx=AppFixture();self.fx.seed("Embedding-v1",embedding_capabilities(),"BAAI/bge-m3");self.service=self.fx.app.embeddings
        self.body={"model":"Embedding-v1","input":"a","dimensions":1024,"encoding_format":"float"}
    def tearDown(self):self.fx.close()

    def test_invalid_base64_is_502_provider_contract_error(self):
        class BadB64(FakeAdapter):
            def embed(self,model,request):return {"object":"list","data":[{"object":"embedding","index":0,"embedding":"@@@notb64$$$"}],"model":model,"usage":{"prompt_tokens":1,"total_tokens":1}}
        self.service._adapter=lambda _:BadB64()
        with self.assertRaises(ApiError) as cm:self.service.create("p","b64",dict(self.body,encoding_format="base64"))
        self.assertEqual((cm.exception.status,cm.exception.code),(502,"provider_contract_error"))

    def test_empty_vector_is_502_provider_contract_error(self):
        class EmptyVec(FakeAdapter):
            def embed(self,model,request):return {"object":"list","data":[{"object":"embedding","index":0,"embedding":[]}],"model":model,"usage":{"prompt_tokens":1,"total_tokens":1}}
        self.service._adapter=lambda _:EmptyVec()
        with self.assertRaises(ApiError) as cm:self.service.create("p","empty",self.body)
        self.assertEqual((cm.exception.status,cm.exception.code),(502,"provider_contract_error"))

    def test_unsupported_dimensions_code_and_param(self):
        with self.assertRaises(ApiError) as cm:self.service.create("p","dims",dict(self.body,dimensions=8))
        self.assertEqual((cm.exception.status,cm.exception.code,cm.exception.param),(400,"unsupported_dimensions","dimensions"))

    def test_unknown_model_is_404_model_not_found(self):
        with self.assertRaises(ApiError) as cm:self.service.create("p","nomodel",dict(self.body,model="Nope"))
        self.assertEqual((cm.exception.status,cm.exception.code),(404,"model_not_found"))
