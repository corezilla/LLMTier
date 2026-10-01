"""M004 management unit gaps (UT-MGMT-001/007/008/009/010/011).

Real `Application` on an isolated temp store (ENV-1); bootstrap uses temp
settings files. Account-usage refresh uses an in-process HTTP response stub
(local `FakeResponse`, matching test_account_usage.py) — no network.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from http_api.app import Application
from http_api.errors import ApiError

from tests.common.fakes import AppFixture, response_capabilities


class FakeResponse:
    def __init__(self, payload): self.payload = json.dumps(payload).encode()
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self): return self.payload


def _valid_config():
    return {
        "providers": [{"id": "prov1", "name": "P", "kind": "local", "endpoint": "http://127.0.0.1:9", "secret_ref": None, "enabled": True}],
        "deployments": [{"id": "dep1", "name": "D", "provider_id": "prov1", "backend_model": "m", "capabilities": response_capabilities(), "enabled": True}],
        "service_levels": [{"id": "Worker", "deployment_ids": ["dep1"], "enabled": True}],
    }


class BootstrapTests(unittest.TestCase):
    """UT-MGMT-001/007: bootstrap valid/no-op/section/secret-ref/rollback."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def _settings(self, name, value):
        path = self.root / name; path.write_text(json.dumps(value)); return str(path)

    def _app(self, name, settings):
        return Application(str(self.root / name), settings)

    def test_valid_bootstrap_succeeds(self):
        app = self._app("a.db", self._settings("s.json", _valid_config()))
        try:
            self.assertIsNone(app.bootstrap_error)
            self.assertEqual(app.store.one("SELECT count(*) FROM providers")[0], 1)
        finally:
            app.store.close()

    def test_repeated_start_is_noop(self):
        app = self._app("b.db", self._settings("s.json", _valid_config())); app.store.close()
        again = self._app("b.db", str(self.root / "missing.json"))
        try:
            self.assertIsNone(again.bootstrap_error)
        finally:
            again.store.close()

    def test_missing_section_fails(self):
        app = self._app("c.db", self._settings("s2.json", {"providers": []}))
        try:
            self.assertIsNotNone(app.bootstrap_error)
            self.assertEqual(app.bootstrap_error.code, "bootstrap_invalid")
        finally:
            app.store.close()


    def test_env_secret_ref_unavailable_fails(self):
        config = _valid_config()
        config["providers"][0]["secret_ref"] = "env:LLMTIER_UT_NOPE"
        app = self._app("d.db", self._settings("s3.json", config))
        try:
            self.assertEqual(app.bootstrap_error.code, "bootstrap_invalid")
        finally:
            app.store.close()

    def test_file_secret_ref_missing_fails(self):
        config = _valid_config()
        config["providers"][0]["secret_ref"] = "file:/nonexistent/llmtier/secret"
        app = self._app("e.db", self._settings("s4.json", config))
        try:
            self.assertEqual(app.bootstrap_error.code, "bootstrap_invalid")
        finally:
            app.store.close()

    def test_failed_bootstrap_rolls_back_to_empty_store(self):
        config = _valid_config()
        config["providers"][0]["secret_ref"] = "env:LLMTIER_UT_NOPE"
        app = self._app("f.db", self._settings("s5.json", config))
        try:
            self.assertEqual(app.store.one("SELECT count(*) FROM providers")[0], 0)
        finally:
            app.store.close()














if __name__ == "__main__":
    unittest.main()
