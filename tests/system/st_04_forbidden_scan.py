"""ST-04 Forbidden path/header scan (System test plan §4, CT-SCOPE-001 +
CT-BOUNDARY-001).

Inspects OpenAPI document for forbidden path patterns (/call, /admin/v0/...,
admin/legacy), and inspects LLMTier responses for forbidden response
headers (X-Legacy-*, Server-with-version). The legacy /call path must
be absent from OpenAPI; the running LLMTier must not echo it back.
"""
from __future__ import annotations

import json
import os
import re
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
OPENAPI = REPO / "interfaces" / "openapi" / "llmtier-v0.3.openapi.json"
MANIFEST = REPO / "interfaces" / "compatibility" / "compatibility-manifest-v0.3.json"

FORBIDDEN_PATH_PATTERNS = [
    r"^/call$",
    r"^/call/",
    r"^/admin/v0/.*$",
    r"/legacy/",
    r"/admin/v0\.",
]

FORBIDDEN_HEADER_PREFIXES = ("X-Legacy-",)


def _free_port() -> int:
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close()
    return p


def _paths_from_openapi(d):
    paths = set()
    for p, methods in d.get("paths", {}).items():
        for m in methods:
            if m.lower() in {"get", "post", "put", "patch", "delete", "head", "options"}:
                paths.add(p)
    return paths


class ST04ForbiddenPathHeaderScan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.openapi = json.loads(OPENAPI.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cls.openapi_paths = _paths_from_openapi(cls.openapi)
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

    def test_no_legacy_call_path_in_openapi(self):
        offenders = [p for p in self.openapi_paths
                     if any(re.match(pat, p) for pat in FORBIDDEN_PATH_PATTERNS)]
        self.assertEqual(offenders, [],
            f"legacy paths leaked into OpenAPI: {offenders}")

    def test_no_legacy_header_in_healthz(self):
        with urllib.request.urlopen(
                f"http://127.0.0.1:{self.port}/healthz", timeout=5) as r:
            for prefix in FORBIDDEN_HEADER_PREFIXES:
                bad = [k for k in r.headers.keys() if k.lower().startswith(prefix.lower())]
                self.assertEqual(bad, [],
                    f"forbidden response header prefix {prefix} on /healthz: {bad}")
            # server header should not expose the framework version
            server = r.headers.get("Server", "")
            self.assertNotIn("0.3.0", server,
                f"Server header exposes version: {server!r}")

    def test_healthz_no_bearer_secret_echo(self):
        # send a request with a sensitive-looking header; the response
        # must not echo it back in any header or body
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/healthz",
            headers={"X-Custom-Auth": "Bearer probe-secret"})
        with urllib.request.urlopen(req, timeout=5) as r:
            for k, v in r.headers.items():
                self.assertNotIn("probe-secret", v,
                    f"secret echoed in response header {k}")
            self.assertNotIn(b"probe-secret", r.read())

    def test_compatibility_manifest_no_legacy_path(self):
        # The manifest may legitimately mention "legacy" as a field
        # name (e.g. legacy_authority describing what was retired). What
        # is forbidden is *paths* and *headers* referencing legacy.
        manifest_text = MANIFEST.read_text(encoding="utf-8")
        self.assertNotIn('"/call"', manifest_text)
        self.assertNotIn('"/admin/v0', manifest_text)
        # The path fields declared in the manifest must not include
        # the forbidden patterns
        import re
        m = json.loads(manifest_text)
        for cap in m.get("capabilities", []):
            path = cap.get("path", "")
            for pat in FORBIDDEN_PATH_PATTERNS:
                self.assertIsNone(re.match(pat, path),
                    f"manifest capability path {path!r} matches forbidden {pat!r}")


if __name__ == "__main__":
    unittest.main()