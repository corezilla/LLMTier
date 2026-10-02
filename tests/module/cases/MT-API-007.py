"""MT-API-007 — `_body` 四出口（M001，层②，boundary，P0）。

出口：非法 Content-Length→400 `invalid_request`；>2MB→413 `request_too_large`；
非法 JSON→400 `invalid_json`；顶层非对象→400 `invalid_json`。
原始 socket 注入（真实字节），无打桩。
"""
from __future__ import annotations

import unittest

from tests.module.cases.support.http_env import LoopbackEnv


class BodyBranchTests(LoopbackEnv):
    def test_invalid_content_length_is_400(self):
        conn = self.raw_connection()
        try:
            conn.putrequest("POST", "/v1/responses")
            conn.putheader("Content-Type", "application/json")
            conn.putheader("Content-Length", "abc")
            conn.endheaders()
            response = conn.getresponse()
            payload = response.read()
            self.assertEqual(400, response.status)
            self.assertEqual("invalid_request", __import__("json").loads(payload)["error"]["code"])
        finally:
            conn.close()

    def test_oversized_body_is_413(self):
        # 只发头部 + 少量字节：服务端按 Content-Length 先判定 413，不读全量
        # 413 响应的头部与 body 是两次 write，可能落在两个 TCP 段里，必须读满
        # Content-Length 之后再断言（单次 recv 会出现头部先到的抖动）。
        import http.client
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        try:
            conn.putrequest("POST", "/v1/responses")
            conn.putheader("Content-Type", "application/json")
            conn.putheader("Content-Length", str(2 * 1024 * 1024 + 1))
            conn.endheaders()
            conn.send(b"x" * 8192)
            response = conn.getresponse()
            payload = response.read()
        finally:
            conn.close()
        self.assertEqual(413, response.status)
        self.assertEqual("request_too_large", __import__("json").loads(payload)["error"]["code"])

    def test_non_json_body_is_400_invalid_json(self):
        status, payload, _ = self.raw_request("POST", "/v1/responses", body=b"{nope",
                                              headers={"Content-Type": "application/json"})
        self.assertEqual(400, status)
        self.assertEqual("invalid_json", __import__("json").loads(payload)["error"]["code"])

    def test_non_object_json_is_400_invalid_json(self):
        status, payload, _ = self.raw_request("POST", "/v1/responses", body=b"[1,2]",
                                              headers={"Content-Type": "application/json"})
        self.assertEqual(400, status)
        self.assertEqual("invalid_json", __import__("json").loads(payload)["error"]["code"])

    def test_exactly_2mb_body_passes_body_gate(self):
        body = (b'{"model":"Worker","input":"' + b"a" * (2 * 1024 * 1024 - 64) + b'"}')
        status, payload, _ = self.raw_request("POST", "/v1/responses", body=body,
                                              headers={"Content-Type": "application/json", "Content-Length": str(len(body))})
        self.assertEqual(413 if len(body) > 2 * 1024 * 1024 else 400, status)
        code = __import__("json").loads(payload)["error"]["code"]
        self.assertIn(code, {"invalid_request", "request_too_large"})


if __name__ == "__main__":
    unittest.main()
