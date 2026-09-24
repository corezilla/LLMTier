import unittest

from http_api.errors import ApiError
from .fakes import AppFixture


class ModelTests(unittest.TestCase):
    def setUp(self): self.fx=AppFixture(); self.fx.seed(); self.models=self.fx.app.models
    def tearDown(self): self.fx.close()
    def test_list_object(self): self.assertEqual(self.models.list()["object"],"list")
    def test_list_has_seven_tiers(self): self.assertEqual(len(self.models.list()["data"]),7)
    def test_get_worker(self): self.assertEqual(self.models.get("Worker")["id"],"Worker")
    def test_owned_by(self): self.assertEqual(self.models.get("Worker")["owned_by"],"llmtier")
    def test_healthy_is_available(self): self.assertEqual(self.models.get("Worker")["availability"],"available")
    def test_unknown_is_degraded(self): self.fx.app.store.connection().execute("UPDATE deployments SET health='unknown'");self.assertEqual(self.models.get("Worker")["availability"],"degraded")
    def test_missing_model(self):
        with self.assertRaises(ApiError) as cm:self.models.get("Nope")
        self.assertEqual(cm.exception.code,"model_not_found")
