"""ST-23 Queue full triggers 429 (System test plan §4).

Verifies that when tier queue (max 32) is full, the 33rd concurrent request
gets 429 immediately without waiting.
"""
from __future__ import annotations

import json
import os
import signal
import socket
import sqlite3
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


class ST23QueueFull429(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory()
        root = Path(cls.work.name)
        settings = {
            "providers": [{
                "id": "provider_queue_test",
                "name": "Queue Test Provider",
                "kind": "local",
                "endpoint": "http://127.0.0.1:9000",
                "secret_ref": "file:/Users/ben/.omlx/api_key.txt",
                "enabled": True,
            }],
            "deployments": [{
                "id": "dep_queue_test",
                "name": "Queue Test Deployment",
                "provider_id": "provider_queue_test",
                "backend_model": "test-model",
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
                "id": "Worker",
                "deployment_ids": ["dep_queue_test"],
            }],
        }
        (root / "settings.json").write_text(json.dumps(settings))
        cls.db = root / "state.sqlite3"
        cls.port = _free_port()
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "src")
        env["LLMTIER_TRUSTED_LAN_MODE"] = "1"
        env["LLMTIER_SLOW_ADAPTER_DELAY"] = "2.0"
        cls.proc = subprocess.Popen(
            ["/usr/local/bin/python3", "-m", "llmtier_v03",
             "--host", "127.0.0.1", "--port", str(cls.port),
             "--database", str(cls.db),
             "--settings", str(root / "settings.json")],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                r = urllib.request.urlopen(
                    f"http://127.0.0.1:{cls.port}/v1/models", timeout=1)
                if r.status == 200:
                    break
            except (urllib.error.URLError, ConnectionError):
                pass
            time.sleep(0.2)
        else:
            cls.proc.kill()
            raise RuntimeError("LLMTier did not become ready within 30s")

        import sqlite3
        with sqlite3.connect(str(cls.db)) as con:
            con.execute("UPDATE deployments SET health='healthy' WHERE id='dep_queue_test'")
            con.execute("""
                UPDATE provider_usage_profiles 
                SET max_concurrent_requests=1, min_request_interval_ms=0, requests_per_minute=0
                WHERE provider_id='provider_queue_test'
            """)
            con.commit()

    @classmethod
    def tearDownClass(cls):
        if cls.proc.poll() is None:
            cls.proc.send_signal(signal.SIGTERM)
            try:
                cls.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                cls.proc.kill()
        cls.work.cleanup()

    def test_33rd_request_gets_429_immediately(self):
        import sqlite3
        with sqlite3.connect(str(self.db)) as con:
            con.execute("UPDATE deployments SET health='healthy' WHERE id='dep_queue_test'")
            con.execute("UPDATE provider_usage_profiles SET max_concurrent_requests=1 WHERE provider_id='provider_queue_test'")
            con.execute("UPDATE deployment_runtime_profiles SET max_in_flight=1 WHERE deployment_id='dep_queue_test'")
            con.commit()

        results = []
        lock = threading.Lock()

        def one_call(i):
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{self.port}/v1/responses",
                    data=json.dumps({
                        "model": "Worker",
                        "input": [{"role": "user", "content": f"req {i}"}],
                        "stream": True,
                        "store": False,
                        "max_output_tokens": 16,
                    }).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST")
                start = time.time()
                try:
                    with urllib.request.urlopen(req, timeout=120) as r:
                        code = r.status
                except urllib.error.HTTPError as e:
                    code = e.code
                elapsed = time.time() - start
                with lock:
                    results.append((i, code, elapsed))
            except Exception as e:
                with lock:
                    results.append((i, -1, str(e)))

        threads = [threading.Thread(target=one_call, args=(i,))
                   for i in range(35)]
        start = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        total_elapsed = time.time() - start

        codes = [r[1] for r in results]
        first_429_time = next((r[2] for r in results if r[1] == 429), None)

        success_count = sum(1 for c in codes if c == 200)
        rate_limited_count = sum(1 for c in codes if c == 429)

        self.assertGreaterEqual(rate_limited_count, 1,
            f"Expected at least one 429; got codes: {codes}")
        if first_429_time is not None:
            self.assertLess(first_429_time, 2.0,
                f"429 should come immediately (<2s); got {first_429_time:.2f}s")
        self.assertGreaterEqual(success_count, 1,
            f"At least some requests should succeed; got {success_count}")
        results = []
        lock = threading.Lock()

        def one_call(i):
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{self.port}/v1/responses",
                    data=json.dumps({
                        "model": "Worker",
                        "input": [{"role": "user", "content": f"req {i}"}],
                        "stream": True,
                        "store": False,
                        "max_output_tokens": 16,
                    }).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST")
                start = time.time()
                try:
                    with urllib.request.urlopen(req, timeout=10) as r:
                        code = r.status
                except urllib.error.HTTPError as e:
                    code = e.code
                elapsed = time.time() - start
                with lock:
                    results.append((i, code, elapsed))
            except Exception as e:
                with lock:
                    results.append((i, -1, str(e)))

        threads = [threading.Thread(target=one_call, args=(i,))
                   for i in range(35)]
        start = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        total_elapsed = time.time() - start

        codes = [r[1] for r in results]
        first_429_time = next((r[2] for r in results if r[1] == 429), None)

        success_count = sum(1 for c in codes if c == 200)
        rate_limited_count = sum(1 for c in codes if c == 429)

        self.assertGreaterEqual(rate_limited_count, 1,
            f"Expected at least one 429; got codes: {codes}")
        if first_429_time is not None:
            self.assertLess(first_429_time, 2.0,
                f"429 should come immediately (<2s); got {first_429_time:.2f}s")
        self.assertGreaterEqual(success_count, 1,
            f"At least some requests should succeed; got {success_count}")


if __name__ == "__main__":
    unittest.main()
