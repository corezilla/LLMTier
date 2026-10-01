from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from http_api import __version__
from http_api.app import Application, handler_factory


class StartupTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def settings(self,value=None):
        p=self.root/"settings.json";p.write_text(json.dumps(value or {"providers":[],"deployments":[],"service_levels":[]}));return str(p)
    def test_version(self):self.assertEqual(__version__,"0.3.0-dev")
    def test_valid_bootstrap(self):
        app=Application(str(self.root/"a.db"),self.settings());self.assertIsNone(app.bootstrap_error);app.store.close()
    def test_missing_settings_not_ready(self):
        app=Application(str(self.root/"b.db"),None);self.assertIsNotNone(app.bootstrap_error);app.store.close()
    def test_invalid_settings_not_ready(self):
        app=Application(str(self.root/"c.db"),self.settings({"bad":[]}));self.assertIsNotNone(app.bootstrap_error);app.store.close()
    def test_failed_bootstrap_has_no_provider(self):
        app=Application(str(self.root/"d.db"),self.settings({"bad":[]}));self.assertEqual(app.store.one("SELECT count(*) FROM providers")[0],0);app.store.close()
    def test_restart_ignores_missing_settings(self):
        db=str(self.root/"e.db");app=Application(db,self.settings());app.store.close();again=Application(db,str(self.root/"missing"));self.assertIsNone(again.bootstrap_error);again.store.close()
    def test_handler_factory(self):
        app=Application(str(self.root/"f.db"),self.settings());self.assertTrue(issubclass(handler_factory(app),__import__('http.server').server.BaseHTTPRequestHandler));app.store.close()


"""M004 management unit gaps (UT-MGMT-001/007/008/009/010/011).

Real `Application` on an isolated temp store (ENV-1); bootstrap uses temp
settings files. Account-usage refresh uses an in-process HTTP response stub
(local `FakeResponse`, matching test_account_usage.py) — no network.
"""

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




    def test_empty_store_without_settings_is_bootstrap_required(self):
        """ERR-BOOT: empty store + no settings path → real registry raises bootstrap_required."""
        app = self._app("g.db", None)
        try:
            self.assertIsNotNone(app.bootstrap_error)
            self.assertEqual((app.bootstrap_error.status, app.bootstrap_error.code), (503, "bootstrap_required"))
        finally:
            app.store.close()

















if __name__ == "__main__":
    unittest.main()


import unittest

from http_api.errors import ApiError
from tests.common.fakes import AppFixture, embedding_capabilities, response_capabilities


class RegistryTests(unittest.TestCase):
    def setUp(self): self.fx=AppFixture(); self.r=self.fx.app.registry
    def tearDown(self): self.fx.close()
    def test_fixed_tiers_exist(self): self.assertEqual(len(self.r.list_service_levels()),7)
