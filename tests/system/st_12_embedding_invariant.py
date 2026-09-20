"""ST-12 Slinky embedding invariant (System test plan §4, CT-EMB-001).

Runs /v1/embeddings 5 times and asserts:
- every response has data[0].embedding of length 1024
- no NaN/Inf in any finite response
- if the path is unavailable, skipTest BLOCKED

The in-process fixture seeds a provider_local + bge-m3 deployment bound
to the Embedding-v1 tier. The DB default for deployments.health is
"unknown"; routing.admit only considers "healthy" candidates. The
fixture must therefore UPDATE deployments.health='healthy' after
bootstrap so the embedding path is exercised.
"""
from __future__ import annotations

import json
import math
import os
import signal
import socket
import sqlite3
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


# Settings template; secret_ref is patched in setUpClass once the
# key file path is known (it lives in a tempdir).
EMBEDDING_SETTINGS = {
    "providers": [
        {
            "id": "provider_local",
            "name": "Local OMLX",
            "kind": "local",
            "endpoint": "http://127.0.0.1:9100",
            "secret_ref": "file:SET_AT_RUNTIME",
            "enabled": True,
            "usage": {"usage_provider": "local"},
        },
    ],
    "deployments": [
        {
            "id": "dep_local_bge_m3",
            "name": "BGE-M3 Embedding",
            "provider_id": "provider_local",
            "backend_model": "bge-m3",
            "capabilities": {
                "responses": False,
                "embeddings": True,
                "tools": False,
                "structured_outputs": False,
                "input_modalities": ["text"],
                "output_modalities": ["embedding"],
                "context_window": None,
                "max_output_tokens": None,
                "embedding_space_id": "bge-m3-dense-1024-v1",
                "embedding_dimensions": [1024],
                "embedding_max_batch_inputs": 32,
                "embedding_max_input_tokens": 8192,
            },
            "enabled": True,
        },
    ],
    "service_levels": [
        {
            "id": "Embedding-v1",
            "deployment_ids": ["dep_local_bge_m3"],
            "enabled": True,
        },
    ],
}


class ST12EmbeddingInvariant(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # OMLX must be reachable with the configured api_key. Skip
        # BLOCKED otherwise. The probe uses the same key that the case
        # fixture will install for LLMTier.
        omlx_key = ""
        for cand in (Path("/Users/mp/LLMTier-dev/secrets/omlx-secret-key.txt"),
                     Path("/Users/mlp/LLMTier-dev/secrets/omlx-secret-key.txt"),
                     Path.home() / ".omlx" / "settings.json",
                     Path("/Users/ben/.omlx/settings.json")):
            if cand.exists():
                try:
                    if cand.name == "settings.json":
                        settings = json.loads(cand.read_text())
                        omlx_key = settings.get("auth", {}).get("api_key", "")
                    else:
                        omlx_key = cand.read_text().strip()
                except Exception:
                    omlx_key = ""
                if omlx_key:
                    break
        if not omlx_key:
            raise unittest.SkipTest(
                "OMLX api_key not found; cannot exercise real embedding path")
        cls.omlx_key = omlx_key
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:9100/v1/models",
                headers={"Authorization": f"Bearer {omlx_key}"})
            with urllib.request.urlopen(req, timeout=3) as r:
                if r.status != 200:
                    raise unittest.SkipTest(
                        f"OMLX /v1/models with configured key returned {r.status}")
        except (urllib.error.URLError, ConnectionError) as e:
            raise unittest.SkipTest(
                f"OMLX unreachable on 127.0.0.1:9100 ({e}); "
                "ST-12 requires OMLX to exercise real embedding path")

        cls.work = tempfile.TemporaryDirectory()
        root = Path(cls.work.name)
        # Write the key file FIRST so the bootstrap path check
        # (line 70 in registry.py) finds it when LLMTier starts.
        (root / "llmtier_test_bge_key.txt").write_text(cls.omlx_key)
        # Now write settings pointing at the existing key file.
        abs_key = str(root / "llmtier_test_bge_key.txt")
        tmp_settings = dict(EMBEDDING_SETTINGS)
        tmp_settings["providers"][0]["secret_ref"] = f"file:{abs_key}"
        (root / "settings.json").write_text(json.dumps(tmp_settings))
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
                break
            except (urllib.error.URLError, ConnectionError):
                time.sleep(0.2)
        else:
            cls.proc.kill()
            raise RuntimeError("LLMTier did not start within 30s")

        # Bootstrap defaults deployments.health='unknown'; routing.admit
        # only dispatches to health='healthy'. Mark bge-m3 healthy so
        # the admission path is exercised.
        with sqlite3.connect(str(cls.db)) as con:
            con.execute("UPDATE deployments SET health='healthy' WHERE id='dep_local_bge_m3'")
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

    def _embed(self, text):
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/v1/embeddings",
            data=json.dumps({"model": "Embedding-v1", "input": text}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_embedding_invariants(self):
        results = [self._embed(f"text {i}") for i in range(5)]
        ok_results = [(s, b) for s, b in results if s == 200 and b.get("data")]
        if not ok_results:
            for s, b in results:
                if s not in (404, 503, 400, 401):
                    self.fail(
                        f"unexpected status {s} with body {b!r}; "
                        "expected 200 with data, or 404/503/400/401 when provider is unconfigured")
            raise unittest.SkipTest(
                f"no usable provider response (statuses="
                f"{[s for s, _ in results]}); likely OMLX bearer not configured. "
                "Run on m5air where the api_key is properly mounted.")
        self.assertEqual(len(ok_results), 5)
        for s, b in ok_results:
            data = b["data"]
            self.assertEqual(len(data), 1)
            emb = data[0]["embedding"]
            self.assertEqual(len(emb), 1024,
                f"expected 1024-dim BGE-M3 embedding, got {len(emb)}")
            for v in emb:
                self.assertFalse(math.isnan(v), "NaN in embedding")
                self.assertFalse(math.isinf(v), "Inf in embedding")
            self.assertEqual(b.get("model"), "Embedding-v1")


if __name__ == "__main__":
    unittest.main()