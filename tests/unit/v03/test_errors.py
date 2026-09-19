import unittest

from llmtier_v03.errors import ApiError, require


class ErrorTests(unittest.TestCase):
    def test_status(self):self.assertEqual(ApiError(400,"x","m").status,400)
    def test_client_type(self):self.assertEqual(ApiError(400,"x","m").envelope()["error"]["type"],"request_error")
    def test_server_type(self):self.assertEqual(ApiError(500,"x","m").envelope()["error"]["type"],"server_error")
    def test_code(self):self.assertEqual(ApiError(400,"code","m").envelope()["error"]["code"],"code")
    def test_param(self):self.assertEqual(ApiError(400,"x","m","field").envelope()["error"]["param"],"field")
    def test_require_true(self):self.assertIsNone(require(True,400,"x","m"))
    def test_require_false(self):
        with self.assertRaises(ApiError) as cm:require(False,422,"x","m")
        self.assertEqual(cm.exception.status,422)
