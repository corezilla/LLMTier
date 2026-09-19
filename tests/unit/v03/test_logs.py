import unittest

from .fakes import AppFixture


class LogTests(unittest.TestCase):
    def setUp(self):self.fx=AppFixture();self.logs=self.fx.app.logs
    def tearDown(self):self.fx.close()
    def page(self,**kw):return self.logs.page(since="2000-01-01T00:00:00Z",until="2100-01-01T00:00:00Z",**kw)
    def test_record(self):self.logs.record("info","m","e","hello");self.assertEqual(self.page()["data"][0]["message"],"hello")
    def test_bearer_redacted(self):self.logs.record("info","m","e","Bearer abcdefghijklmnop");self.assertNotIn("abcdefghijklmnop",self.page()["data"][0]["message"])
    def test_authorization_redacted(self):self.logs.record("info","m","e","Authorization header");self.assertNotIn("Authorization",self.page()["data"][0]["message"])
    def test_newline_removed(self):self.logs.record("info","m","e","a\nb");self.assertEqual(self.page()["data"][0]["message"],"a b")
    def test_message_bounded(self):self.logs.record("info","m","e","x"*900);self.assertLessEqual(len(self.page()["data"][0]["message"]),512)
    def test_filter_level(self):self.logs.record("error","m","e","x");self.logs.record("info","m","e","y");self.assertTrue(all(x["level"]=="error" for x in self.page(level="error")["data"]))
    def test_filter_module(self):self.logs.record("info","one","e","x");self.logs.record("info","two","e","y");self.assertTrue(all(x["module"]=="one" for x in self.page(module="one")["data"]))
