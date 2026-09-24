import unittest

from llmtier_v03.errors import ApiError
from .fakes import AppFixture, embedding_capabilities, response_capabilities


class RegistryTests(unittest.TestCase):
    def setUp(self): self.fx=AppFixture(); self.r=self.fx.app.registry
    def tearDown(self): self.fx.close()
    def test_fixed_tiers_exist(self): self.assertEqual(len(self.r.list_service_levels()),7)
    def test_provider_round_trip(self):
        p,e=self.r.create_provider({"name":"p","kind":"cloud","endpoint":"https://example.test","secret_ref":None,"enabled":True}); self.assertEqual(self.r.get_provider(p["id"]),(p,e))
    def test_provider_secret_not_returned(self):
        p,_=self.r.create_provider({"name":"p","kind":"cloud","endpoint":"https://example.test","secret_ref":"env:X","enabled":True}); self.assertNotIn("secret_ref",p); self.assertTrue(p["has_secret"])
    def test_duplicate_provider_rejected(self):
        body={"name":"p","kind":"local","endpoint":"http://x","secret_ref":None,"enabled":True}; self.r.create_provider(body)
        with self.assertRaises(ApiError) as cm:self.r.create_provider(body)
        self.assertEqual(cm.exception.status,409)
    def test_provider_stale_etag(self):
        p,_=self.r.create_provider({"name":"p","kind":"local","endpoint":"http://x","secret_ref":None,"enabled":True})
        with self.assertRaises(ApiError) as cm:self.r.update_provider(p["id"],{"enabled":False},'"bad"')
        self.assertEqual(cm.exception.status,412)
    def test_deployment_requires_provider(self):
        with self.assertRaises(ApiError): self.r.create_deployment({"name":"d","provider_id":"missing","backend_model":"m","capabilities":response_capabilities(),"enabled":True})
    def test_deployment_capabilities_exact(self):
        p,_=self.r.create_provider({"name":"p","kind":"local","endpoint":"http://x","secret_ref":None,"enabled":True}); caps=response_capabilities();caps.pop("tools")
        with self.assertRaises(ApiError): self.r.create_deployment({"name":"d","provider_id":p["id"],"backend_model":"m","capabilities":caps,"enabled":True})
    def test_inference_tier_rejects_embedding(self):
        _,d=self.fx.seed("Embedding-v1",embedding_capabilities(),"BAAI/bge-m3")
        _,etag=self.r.get_service_level("Worker")
        with self.assertRaises(ApiError): self.r.update_service_level("Worker",{"deployment_ids":[d["id"]]},etag)
    def test_embedding_space_is_frozen(self):
        p,_=self.r.create_provider({"name":"p","kind":"local","endpoint":"http://x","secret_ref":None,"enabled":True}); caps=embedding_capabilities();caps["embedding_space_id"]="wrong"
        d,_=self.r.create_deployment({"name":"d","provider_id":p["id"],"backend_model":"BAAI/bge-m3","capabilities":caps,"enabled":True}); _,etag=self.r.get_service_level("Embedding-v1")
        with self.assertRaises(ApiError):self.r.update_service_level("Embedding-v1",{"deployment_ids":[d["id"]]},etag)
    def test_embedding_provider_model_alias_is_allowed(self):
        p,_=self.r.create_provider({"name":"p","kind":"local","endpoint":"http://x/v1","secret_ref":None,"enabled":True})
        d,_=self.r.create_deployment({"name":"d","provider_id":p["id"],"backend_model":"bge-m3","capabilities":embedding_capabilities(),"enabled":True})
        _,etag=self.r.get_service_level("Embedding-v1")
        value,_=self.r.update_service_level("Embedding-v1",{"deployment_ids":[d["id"]]},etag)
        self.assertEqual(value["deployment_ids"],[d["id"]])
    def test_fixed_tier_delete_rejected(self):
        with self.assertRaises(ApiError) as cm:self.r.delete_service_level("Worker",None)
        self.assertEqual(cm.exception.code,"fixed_service_level")
    def test_unknown_deployment_reference_is_400(self):
        _,etag=self.r.get_service_level("Worker")
        with self.assertRaises(ApiError) as cm:self.r.update_service_level("Worker",{"deployment_ids":["missing"]},etag)
        self.assertEqual((cm.exception.status,cm.exception.code),(400,"invalid_request"))
    def test_deployment_capability_edit_recomputes_bound_tier(self):
        _,d=self.fx.seed("Worker")
        caps={**response_capabilities(),"tools":False}
        self.r.update_deployment(d["id"],{"capabilities":caps},self.r.get_deployment(d["id"])[1])
        level,_=self.r.get_service_level("Worker")
        self.assertFalse(level["capabilities"]["tools"])
    def test_deployment_capability_edit_conflict_rolls_back(self):
        _,d=self.fx.seed("Worker")
        before=self.r.get_deployment(d["id"])[0]["capabilities"]
        bad={**response_capabilities(),"responses":False}
        with self.assertRaises(ApiError) as cm:self.r.update_deployment(d["id"],{"capabilities":bad},self.r.get_deployment(d["id"])[1])
        self.assertEqual(cm.exception.status,409)
        self.assertEqual(self.r.get_deployment(d["id"])[0]["capabilities"],before)
