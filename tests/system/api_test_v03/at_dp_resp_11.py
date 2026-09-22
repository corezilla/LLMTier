"""Case ID: DP-RESP-11

Endpoint: POST /v1/responses
Upstream Provider: 故障注入（503）
Model: Worker（指向故障 provider）
Auth: Bearer dev-data

目标：验证上游 provider 返回 503 时 LLMTier 的错误传播行为。

实现：
- B-class 测试：在临时实例中，将 prov_b 的 endpoint 改为指向测试进程内的 mock server
- mock server 在 127.0.0.1 随机端口监听，永远返回 HTTP 503
- LLMTier 向 prov_b 发请求 → 503 → LLMTier 返回 500 internal_error

断言：
- HTTP 503
- error.code == "model_unavailable"
- error.message 包含 "unhealthy"
"""
from __future__ import annotations

import http.server
import socketserver
import threading

import pytest


class _503Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        self.send_response(503)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"error": "fault injected"}')

    def log_message(self, fmt, *args):
        pass


class _ThreadedTCPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


class _FaultServer:
    def __init__(self):
        import socket
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        self.server = _ThreadedTCPServer(("127.0.0.1", self.port), _503Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.server.shutdown()


@pytest.mark.api_b
def test_dp_resp_11_upstream_503_propagation(admin_client_b):
    fault = _FaultServer()
    fault.start()
    try:
        fault_url = f"http://127.0.0.1:{fault.port}"
        admin_client_b.patch(
            "/v1/providers/prov_b",
            json={"endpoint": fault_url},
            headers={"If-Match": '"prov_b.v1"'},
        )

        import httpx
        with httpx.Client(base_url=admin_client_b.base_url, headers={"Authorization": "Bearer dev-data"}, timeout=10.0) as api_client:
            resp = api_client.post(
                "/v1/responses",
                json={
                    "model": "Senior",
                    "input": [{"role": "user", "content": "Hello"}],
                    "stream": True,
                    "store": False,
                },
            )
        assert resp.status_code == 503, f"期望 503，实际 {resp.status_code}: {resp.text}"
        err = resp.json().get("error") or {}
        assert err.get("code") == "model_unavailable", f"error.code != 'model_unavailable': {err}"
        assert "unhealthy" in err.get("message", "").lower(), f"message 不含 unhealthy: {err}"
    finally:
        fault.stop()
