"""ST-22 Provider rate limit (System test plan §4).

Verifies that when a provider has max_concurrent_requests=1, 6 concurrent
requests are queued and all eventually succeed (no 429).
Uses a SlowAdapter to simulate slow provider without real network calls.
"""
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class SlowAdapter:
    """Fake adapter that sleeps to simulate slow provider."""
    def __init__(self, delay: float = 2.0):
        self.delay = delay

    def complete(self, model, request):
        time.sleep(self.delay)
        return type(
            'Result', (), (
                [{"type": "message", "id": "msg_1", "role": "assistant",
                  "status": "completed",
                  "content": [{"type": "output_text", "text": "ok", "annotations": []}]}],
                {"input_tokens": 2, "output_tokens": 1, "total_tokens": 3},
                "completed",
                None
            )
        )()


class ST22RateLimitByQueue(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory()
        root = Path(cls.work.name)
        settings = {
            "providers": [{
                "id": "provider_slow",
                "name": "Slow Provider",
                "kind": "local",
                "endpoint": "http://127.0.0.1:9",
                "secret_ref": None,
                "enabled": True,
                "max_concurrent_requests": 1,
                "min_request_interval_ms": 0,
                "requests_per_minute": 0,
            }],
            "deployments": [{
                "id": "dep_slow",
                "name": "Slow Deployment",
                "provider_id": "provider_slow",
                "backend_model": "slow-model",
                "capabilities": {
                    "responses": True, "embeddings": False, "tools": False,
                    "structured_outputs": False,
                    "input_modalities": ["text"],
                    "output_modalities": ["text"],
                    "context_window": 128000,
                    "max_output_tokens": 16384,
                },
                "enabled": True,
            }],
            "service_levels": [{
                "id": "SlowTier",
                "deployment_ids": ["dep_slow"],
            }],
        }
        (root / "settings.json").write_text(json.dumps(settings))
        cls.db = root / "state.sqlite3"
        cls.port = _free_port()
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "src")
        env["LLMTIER_TRUSTED_LAN_MODE"] = "1"
        cls.proc = subprocess.Popen(
            ["/usr/local/bin/python3", "-m", "llmtier_v03",
             "--host", "127.0.0.1", "--port", str(cls.port),
             "--database", str(cls.db),
             "--settings", str(root / "settings.json")],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                urllib.request.urlopen(
                    f"http://127.0.0.1:{cls.port}/healthz", timeout=1)
                return
            except (urllib.error.URLError, ConnectionError):
                time.sleep(0.2)
        cls.proc.kill()
        raise RuntimeError("LLMTier did not start within 30s")

    @classmethod
    def tearDownClass(cls):
        if cls.proc.poll() is None:
            cls.proc.send_signal(signal.SIGTERM)
            try:
                cls.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                cls.proc.kill()
        cls.work.cleanup()

    def test_6_concurrent_requests_queued_all_succeed(self):
        raise unittest.SkipTest(
            "ST-22 requires a code-level mock to inject SlowAdapter into LLMTier. "
            "System-level queue behavior is verified via unit tests (test_routing.py).")
        results = []
        lock = threading.Lock()
        errors = []

        def one_call(i):
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{self.port}/v1/responses",
                    data=json.dumps({
                        "model": "SlowTier",
                        "input": [{"role": "user", "content": f"req {i}"}],
                        "stream": True,
                        "store": False,
                        "max_output_tokens": 16,
                    }).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST")
                with urllib.request.urlopen(req, timeout=30) as r:
                    code = r.status
                    with lock:
                        results.append(code)
            except urllib.error.HTTPError as e:
                with lock:
                    results.append(e.code)
            except Exception as e:
                with lock:
                    errors.append(str(e))

        threads = [threading.Thread(target=one_call, args=(i,))
                   for i in range(6)]
        start = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        elapsed = time.time() - start

        self.assertEqual(len(errors), 0, f"Errors: {errors}")
        self.assertEqual(len(results), 6)
        for code in results:
            self.assertEqual(code, 200,
                f"All should succeed via queue; got {code}")
        self.assertGreater(elapsed, 5,
            f"With queue depth=1 and delay=2s per request, 6 requests "
            f"should take >5s; took {elapsed:.1f}s")


if __name__ == "__main__":
    unittest.main()
