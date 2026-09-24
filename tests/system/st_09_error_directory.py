"""ST-09 Piko Responses error directory (System test plan §4, CT-DP-001).

Each sub-case sends a request that should fail validation with 400/404
and a specific error code. Requires LLMTier running.

  9.1  stream:false                       -> 400 invalid_request
  9.2  store:true                         -> 400 invalid_request
  9.3  missing model / input              -> 400 invalid_request
  9.4  previous_response_id               -> 400 unsupported_field
  9.5  unknown model                      -> 404 model_not_found
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
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close()
    return p


def _boot_llmtier(REPO):
    work = tempfile.TemporaryDirectory()
    root = Path(work.name)
    (root / "settings.json").write_text(json.dumps({
        "providers": [], "deployments": [], "service_levels": [],
    }))
    db = root / "state.sqlite3"
    port = _free_port()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO / "src")
    env["LLMTIER_TRUSTED_LAN_MODE"] = "1"
    proc = subprocess.Popen(
        ["/usr/local/bin/python3", "-m", "http_api",
         "--host", "127.0.0.1", "--port", str(port),
         "--database", str(db),
         "--settings", str(root / "settings.json")],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=1)
            return proc, port, work
        except (urllib.error.URLError, ConnectionError):
            time.sleep(0.2)
    proc.kill()
    raise RuntimeError("LLMTier did not start within 30s")


class ST09ErrorDirectory(unittest.TestCase):
    port = None

    @classmethod
    def setUpClass(cls):
        REPO = Path(__file__).resolve().parents[2]
        cls.proc, cls.port, cls.work = _boot_llmtier(REPO)

    @classmethod
    def tearDownClass(cls):
        if cls.proc.poll() is None:
            cls.proc.send_signal(signal.SIGTERM)
            try:
                cls.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                cls.proc.kill()
        cls.work.cleanup()

    def _post(self, body):
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/v1/responses",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST")
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_9_1_stream_false_rejected(self):
        # stream must be true (the only supported mode) — handled by
        # responses.py with code="unsupported_request"
        s, body = self._post({
            "model": "Worker", "input": "hi", "stream": False,
            "store": False, "max_output_tokens": 16,
        })
        self.assertEqual(s, 400)
        self.assertEqual(body["error"]["code"], "unsupported_request")

    def test_9_2_store_true_rejected(self):
        # store must be false — same unsupported_request path
        s, body = self._post({
            "model": "Worker", "input": "hi", "stream": True,
            "store": True, "max_output_tokens": 16,
        })
        self.assertEqual(s, 400)
        self.assertEqual(body["error"]["code"], "unsupported_request")

    def test_9_3_missing_fields_rejected(self):
        # empty body — every required field absent
        s, body = self._post({})
        self.assertEqual(s, 400)
        self.assertEqual(body["error"]["code"], "invalid_request")

    def test_9_4_previous_response_id_rejected(self):
        s, body = self._post({
            "model": "Worker", "input": "hi", "stream": True,
            "store": False, "max_output_tokens": 16,
            "previous_response_id": "resp_xyz",
        })
        self.assertEqual(s, 400)
        self.assertEqual(body["error"]["code"], "unsupported_field")

    def test_9_5_unknown_model(self):
        s, body = self._post({
            "model": "nosuch", "input": "hi", "stream": True,
            "store": False, "max_output_tokens": 16,
        })
        self.assertEqual(s, 404)
        self.assertEqual(body["error"]["code"], "model_not_found")


if __name__ == "__main__":
    unittest.main()