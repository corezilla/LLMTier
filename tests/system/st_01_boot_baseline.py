"""ST-01 启服 baseline (System test plan §4).

Run an LLMTier process in a temp dir, hit /healthz 5x and /readyz 5x,
check 7 tier availability, FD ≤ 80. Uses in-process subprocess so it
runs on the local machine without m5air.
"""
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import tempfile
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


class ST01BootBaseline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory()
        root = Path(cls.work.name)
        settings = root / "settings.json"
        settings.write_text(json.dumps({
            "providers": [],
            "deployments": [],
            "service_levels": [],
        }))
        cls.db = root / "state.sqlite3"
        cls.port = _free_port()
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "src")
        env["LLMTIER_TRUSTED_LAN_MODE"] = "1"
        cls.proc = subprocess.Popen(
            ["/usr/local/bin/python3", "-m", "llmtier_v03",
             "--host", "127.0.0.1",
             "--port", str(cls.port),
             "--database", str(cls.db),
             "--settings", str(settings)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{cls.port}/healthz", timeout=1)
                return
            except (urllib.error.URLError, ConnectionError):
                time.sleep(0.2)
        cls.proc.kill()
        raise RuntimeError("LLMTier did not become healthy within 30s")

    @classmethod
    def tearDownClass(cls):
        if cls.proc.poll() is None:
            cls.proc.send_signal(signal.SIGTERM)
            try:
                cls.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                cls.proc.kill()
        cls.work.cleanup()

    def _get(self, path):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=5) as r:
            self.assertEqual(r.status, 200, f"{path} -> {r.status}")
            return r

    def test_healthz_5x(self):
        for _ in range(5):
            self._get("/healthz")

    def test_readyz_5x_with_seven_tiers(self):
        # /readyz reflects provider reachability. With no real providers
        # in the in-process test fixture, every tier is "unavailable" and
        # the response is 503 "not_ready". Verify the response shape
        # (7 tier ids, status not_ready) rather than a 200 ready which
        # requires OMLX / real providers (m5air-only).
        import urllib.error
        for _ in range(5):
            try:
                urllib.request.urlopen(
                    f"http://127.0.0.1:{self.port}/readyz", timeout=5)
                self.fail("/readyz should be 503 with empty providers")
            except urllib.error.HTTPError as e:
                self.assertEqual(e.code, 503)
                body = json.loads(e.read())
        self.assertEqual(body["status"], "not_ready")
        ids = sorted(m["id"] for m in body["models"])
        self.assertEqual(ids, ["Associate", "Embedding-v1", "Engineer",
                                "Executor", "Junior", "Senior", "Worker"])
        for m in body["models"]:
            self.assertEqual(m["availability"], "unavailable", m)

    def test_fd_under_80(self):
        out = subprocess.check_output(["lsof", "-p", str(self.proc.pid)]).decode()
        nlines = len([l for l in out.splitlines() if l.strip()])
        self.assertLessEqual(nlines, 80, f"FD too high: {nlines}")


if __name__ == "__main__":
    unittest.main()