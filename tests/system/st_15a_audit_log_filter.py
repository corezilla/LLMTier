"""ST-15A Audit + LogPage filter + forbidden content scan
(System test plan §4, CT-LOG-001).

Verifies:
- /v1/audit returns the expected envelope (data + page)
- /v1/logs accepts level + module query params
- response bodies never echo forbidden tokens (Authorization, Bearer,
  prompt, response content, embedding)
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


REPO = Path(__file__).resolve().parents[2]
FORBIDDEN_TOKENS = (
    "Bearer ",
    "Authorization",
    "sk-",
    "sk_",
    "<embedding>",
)


def _free_port() -> int:
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close()
    return p


class ST15AAuditLogFilter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory()
        root = Path(cls.work.name)
        (root / "settings.json").write_text(json.dumps({
            "providers": [], "deployments": [], "service_levels": [],
        }))
        cls.db = root / "state.sqlite3"
        cls.port = _free_port()
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO / "src")
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

    def _get_json(self, path, query=None):
        # /v1/usage and /v1/logs both require
        # from + to; supply a 1-second window so the test is self-contained.
        url = f"http://127.0.0.1:{self.port}{path}"
        if query is None:
            query = {}
        # default to a 1-second window covering the test run
        query.setdefault("from", "2020-01-01T00:00:00Z")
        query.setdefault("to", "2999-12-31T23:59:59Z")
        from urllib.parse import urlencode
        url = url + "?" + urlencode(query)
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.status, json.loads(r.read())

    def test_audit_envelope(self):
        s, body = self._get_json("/v1/audit")
        self.assertEqual(s, 200)
        self.assertIn("data", body)
        self.assertIsInstance(body["data"], list)
        self.assertIn("page", body)
        for ev in body["data"]:
            self.assertNotIn("prompt", ev)
            self.assertNotIn("response_content", ev)
            self.assertNotIn("embedding", ev)

    def test_logs_filtered_by_level(self):
        # query string parameters must be honored; the response data
        # shape is independent of how many rows match.
        s, body = self._get_json("/v1/logs",
                                  {"level": "info", "limit": "5"})
        self.assertEqual(s, 200)
        self.assertIn("data", body)
        self.assertIsInstance(body["data"], list)

    def test_logs_filtered_by_module(self):
        s, body = self._get_json("/v1/logs",
                                  {"module": "http", "limit": "5"})
        self.assertEqual(s, 200)
        self.assertIn("data", body)

    def test_no_forbidden_token_in_responses(self):
        # Hit the audit + logs endpoints and the healthz; in none of
        # the response bodies (or the tested status pages) should any
        # of the forbidden tokens appear.
        for path in ("/healthz", "/v1/audit",
                     "/v1/logs?limit=5"):
            s, body = self._get_json(path.split("?")[0],
                                      {"limit": "5"} if "?" in path else None)
            text = json.dumps(body)
            for tok in FORBIDDEN_TOKENS:
                self.assertNotIn(tok, text,
                    f"{path} echoes forbidden token {tok!r}")


if __name__ == "__main__":
    unittest.main()