"""MT-MGMT-001 — Registry.bootstrap_settings 组装后引导（M004，层①/层④ T6，normal，P0）。

组装保证：合法 settings→ready；空库无 settings→503 `bootstrap_required`；
重复启动 no-op（bootstrap 审计仅一条）。
"""
from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from http_api.app import Application, handler_factory
from tests.common.fakes import AppFixture


class BootstrapAssemblyTests(unittest.TestCase):
    def _settings_file(self, providers=(), deployments=(), levels=()):
        root = tempfile.mkdtemp()
        path = Path(root) / "settings.json"
        path.write_text(json.dumps({"providers": list(providers), "deployments": list(deployments), "service_levels": list(levels)}))
        return str(path)

    def test_valid_settings_bootstraps_ready(self):
        settings = self._settings_file()
        app = Application(str(Path(tempfile.mkdtemp()) / "state.sqlite3"), settings)
        try:
            self.assertIsNone(app.bootstrap_error)
            levels = app.registry.list_service_levels()
            self.assertEqual(7, len(levels))
        finally:
            app.store.close()

    def test_empty_store_without_settings_is_bootstrap_required(self):
        app = Application(str(Path(tempfile.mkdtemp()) / "state.sqlite3"), None)
        try:
            self.assertIsNotNone(app.bootstrap_error)
            self.assertEqual(("bootstrap_required", 503), (app.bootstrap_error.code, app.bootstrap_error.status))
        finally:
            app.store.close()

    def test_second_startup_is_noop_single_bootstrap_audit(self):
        settings = self._settings_file()
        db = str(Path(tempfile.mkdtemp()) / "state.sqlite3")
        app1 = Application(db, settings)
        app1.store.close()
        app2 = Application(db, settings)
        try:
            self.assertIsNone(app2.bootstrap_error)
            audits = app2.audit.page(limit=100)["data"]
            bootstraps = [a for a in audits if a["action"] == "registry.bootstrap"]
            self.assertEqual(1, len(bootstraps))
        finally:
            app2.store.close()

    def test_readyz_reflects_bootstrap_state(self):
        db = str(Path(tempfile.mkdtemp()) / "state.sqlite3")
        app = Application(db, None)  # 引导失败 → not_ready
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler_factory(app))
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{server.server_address[1]}/readyz")
            try:
                with urllib.request.urlopen(req) as resp:
                    status, payload = resp.status, json.loads(resp.read())
            except urllib.error.HTTPError as exc:
                status, payload = exc.code, json.loads(exc.read())
            self.assertEqual(503, status)
            self.assertEqual("not_ready", payload["status"])
        finally:
            server.shutdown(); server.server_close(); app.store.close()


if __name__ == "__main__":
    unittest.main()
