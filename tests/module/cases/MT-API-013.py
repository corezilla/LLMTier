"""MT-API-013 — 连接重置 RST mid-stream（M001，层②，recovery，P1；§1.5.1 c5）。

ENV-2 真实 socket：客户端 `SO_LINGER 0` 后 `close()` 触发 RST → 服务端
`ConnectionResetError` → `aborted` 终态；进程不崩溃、许可/fd 释放。
"""
from __future__ import annotations

import json
import os
import socket
import struct
import unittest
import urllib.error
import urllib.request

from tests.module.cases.support.http_env import LargeFakeAdapter, LoopbackEnv

BODY = {"model": "Worker", "input": "hello", "stream": True, "store": False}


class ResetTests(LoopbackEnv):
    def _runtime_inflight(self):
        status, runtime, _ = self.request("GET", "/v1/runtime")
        return sum(d["running"] for d in runtime["deployments"].values())

    def _fds(self):
        return len(os.listdir("/dev/fd"))

    def test_rst_mid_stream_aborts_without_crash(self):
        self.fx.app.responses._test_adapter = LargeFakeAdapter()
        baseline_fds = self._fds()
        try:
            payload = json.dumps(BODY).encode()
            sock = socket.create_connection(("127.0.0.1", self.port), timeout=30)
            sock.sendall(
                b"POST /v1/responses HTTP/1.1\r\nHost: 127.0.0.1\r\n"
                b"Content-Type: application/json\r\n"
                b"Content-Length: " + str(len(payload)).encode() + b"\r\n\r\n" + payload
            )
            buf = b""
            while b"response.created" not in buf:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buf += chunk
            self.assertIn(b"X-Request-ID: ", buf)
            request_id = buf.split(b"X-Request-ID: ", 1)[1].split(b"\r\n", 1)[0].decode()
            # 排空在途字节后以 SO_LINGER 0 关闭 → RST
            self.drain(sock)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
            sock.close()

            def aborted_trace():
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/v1/trace/{request_id}", timeout=10) as resp:
                        trace = json.loads(resp.read())
                except urllib.error.HTTPError:
                    return None
                return trace if any(s["stage"] == "aborted" for s in trace["stages"]) else None
            trace = self.wait_for(aborted_trace)
            self.assertIsNotNone(trace)
            aborted = next(s for s in trace["stages"] if s["stage"] == "aborted")
            self.assertEqual("client disconnected", aborted["detail"]["reason"])

            # 进程不崩溃
            status, health, _ = self.request("GET", "/healthz")
            self.assertEqual(200, status)
            # 许可归零、fd 不泄漏
            self.assertTrue(self.wait_for(lambda: self._runtime_inflight() == 0))
            self.assertLessEqual(self._fds(), baseline_fds + 2)
        finally:
            self.fx.app.responses._test_adapter = None


if __name__ == "__main__":
    unittest.main()
