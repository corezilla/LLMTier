"""ST-03 Models exact-case (System test plan §4, CT-MODEL-001).

Asserts:
- /v1/models/Worker       200  (correct case)
- /v1/models/worker       404  (lowercase)
- /v1/models/WORKER       404  (uppercase)
- /v1/models/Senior%20    404  (URL-encoded space; not a valid id)
- /v1/models/<id>         404  (unknown id)

Requires the LLMTier process to be running on a known port. The
shared test fixture class spins up a fresh in-process LLMTier.
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


class ST03ModelsExactCase(unittest.TestCase):
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
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "src")
        env["LLMTIER_TRUSTED_LAN_MODE"] = "1"
        cls.proc = subprocess.Popen(
            ["/usr/local/bin/python3", "-m", "http_api",
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

    def _get_status(self, path):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}")
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def test_correct_case(self):
        # /v1/models/{id} returns a single model dict (200 with "id":"Worker"
        # in the FIXED_TIERS list) regardless of whether any deployment
        # is registered. The point of ST-03 is case-sensitivity, not
        # model availability, so 200 with availability="unavailable" is OK.
        s, body = self._get_status("/v1/models/Worker")
        self.assertEqual(s, 200, f"Worker id should resolve; got {s}")
        if isinstance(body, (bytes, bytearray)):
            data = json.loads(body)
        else:
            data = json.loads(body)
        self.assertEqual(data["id"], "Worker")
        self.assertEqual(data["object"], "model")

    def test_lowercase_rejected(self):
        s, _ = self._get_status("/v1/models/worker")
        self.assertEqual(s, 404)

    def test_uppercase_rejected(self):
        s, _ = self._get_status("/v1/models/WORKER")
        self.assertEqual(s, 404)

    def test_unknown_id_rejected(self):
        s, _ = self._get_status("/v1/models/nosuchmodel")
        self.assertEqual(s, 404)

    def test_url_encoded_space_rejected(self):
        s, _ = self._get_status("/v1/models/Senior%20")
        self.assertEqual(s, 404)


if __name__ == "__main__":
    unittest.main()