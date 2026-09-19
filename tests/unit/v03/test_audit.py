import unittest

from .fakes import AppFixture


class AuditTests(unittest.TestCase):
    def setUp(self):self.fx=AppFixture();self.audit=self.fx.app.audit
    def tearDown(self):self.fx.close()
    def test_record(self):self.audit.record("a","x","t","ok");self.assertEqual(len(self.audit.page()["data"]),2)
    def test_actor(self):self.audit.record("alice","x","t","ok");self.assertEqual(self.audit.page()["data"][0]["actor"],"alice")
    def test_action(self):self.audit.record("a","change","t","ok");self.assertEqual(self.audit.page()["data"][0]["action"],"change")
    def test_target(self):self.audit.record("a","x","resource","ok");self.assertEqual(self.audit.page()["data"][0]["target"],"resource")
    def test_result(self):self.audit.record("a","x","t","failed");self.assertEqual(self.audit.page()["data"][0]["result"],"failed")
    def test_request_id_not_exposed(self):self.audit.record("a","x","t","ok","secret-correlation");self.assertNotIn("request_id",self.audit.page()["data"][0])
    def test_limit(self):
        for i in range(3):self.audit.record("a",str(i),"t","ok")
        self.assertEqual(len(self.audit.page(2)["data"]),2)
