import unittest

from .fakes import AppFixture


class AuditTests(unittest.TestCase):
    def setUp(self):self.fx=AppFixture();self.audit=self.fx.app.audit
    def tearDown(self):self.fx.close()
    def test_record(self):
        before=len(self.audit.page()["data"])
        self.audit.record("a","x","t","ok")
        page=self.audit.page()["data"]
        self.assertEqual(len(page),before+1)
        self.assertEqual(page[0]["action"],"x")
        self.assertEqual(page[0]["actor"],"a")
    def test_actor(self):self.audit.record("alice","x","t","ok");self.assertEqual(self.audit.page()["data"][0]["actor"],"alice")
    def test_action(self):self.audit.record("a","change","t","ok");self.assertEqual(self.audit.page()["data"][0]["action"],"change")
    def test_target(self):self.audit.record("a","x","resource","ok");self.assertEqual(self.audit.page()["data"][0]["target"],"resource")
    def test_result(self):self.audit.record("a","x","t","failed");self.assertEqual(self.audit.page()["data"][0]["result"],"failed")
    def test_request_id_exposed(self):self.audit.record("a","x","t","ok","corr-1");self.assertEqual(self.audit.page()["data"][0]["request_id"],"corr-1")
    def test_limit(self):
        for i in range(3):self.audit.record("a",str(i),"t","ok")
        self.assertEqual(len(self.audit.page(2)["data"]),2)
