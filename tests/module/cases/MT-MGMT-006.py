"""MT-MGMT-006 — bootstrap 五出口 + 回滚 + 固定 tier 幂等（M004，层②/层④ T7，recovery，P0）。

五出口：no-op / required / invalid(缺节) / `env:` 空 / `file:` 缺失；
中途失败→事务回滚空库 + not_ready；`ensure_fixed_tiers` 幂等。
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from http_api.app import Application
from http_api.errors import ApiError
from management.registry import FIXED_TIERS, Registry
from util.store import Store


class BootstrapExitTests(unittest.TestCase):
    def _db(self):
        return str(Path(tempfile.mkdtemp()) / "state.sqlite3")

    def _settings(self, payload):
        root = tempfile.mkdtemp()
        path = Path(root) / "settings.json"
        path.write_text(json.dumps(payload) if isinstance(payload, dict) else payload)
        return str(path)

    def _valid(self, secret_ref=None):
        return {
            "providers": [{"id": "p1", "name": "P1", "kind": "local", "endpoint": "http://127.0.0.1:9",
                           "secret_ref": secret_ref, "enabled": True}],
            "deployments": [{"id": "d1", "name": "D1", "provider_id": "p1", "backend_model": "m",
                             "capabilities": {"responses": True, "embeddings": False, "tools": False,
                                              "structured_outputs": False}, "enabled": True}],
            "service_levels": [{"id": "Worker", "deployment_ids": ["d1"], "enabled": True}],
        }

    def _bootstrap(self, settings_path):
        db = self._db()
        app = Application(db, settings_path)
        error = app.bootstrap_error
        providers = []
        try:
            providers = app.registry.list_providers()
        except ApiError:
            pass
        app.store.close()
        return error, providers, db

    def test_noop_on_bootstrapped_store(self):
        settings = self._settings(self._valid())
        error1, providers1, db = self._bootstrap(settings)
        self.assertIsNone(error1)
        app2 = Application(db, settings)
        try:
            self.assertIsNone(app2.bootstrap_error)
            self.assertEqual(1, len(app2.registry.list_providers()))
        finally:
            app2.store.close()

    def test_bootstrap_required_without_settings(self):
        error, _, _ = self._bootstrap(None)
        self.assertEqual(("bootstrap_required", 503), (error.code, error.status))

    def test_missing_section_is_invalid(self):
        root = tempfile.mkdtemp()
        path = Path(root) / "settings.json"
        path.write_text(json.dumps({"providers": [], "deployments": []}))
        error, _, _ = self._bootstrap(str(path))
        self.assertEqual(("bootstrap_invalid", 503), (error.code, error.status))

    def test_env_empty_secret_is_invalid(self):
        settings = self._settings(self._valid(secret_ref="env:LLMTIER_DEFINITELY_UNSET_XYZ"))
        error, _, _ = self._bootstrap(settings)
        self.assertEqual(("bootstrap_invalid", 503), (error.code, error.status))

    def test_missing_secret_file_is_invalid(self):
        settings = self._settings(self._valid(secret_ref="file:/nonexistent/secret"))
        error, _, _ = self._bootstrap(settings)
        self.assertEqual(("bootstrap_invalid", 503), (error.code, error.status))

    def test_mid_transaction_failure_rolls_back_empty(self):
        # 第二个 deployment 能力非法 → 事务中途失败 → 全量回滚（无半写）
        payload = self._valid()
        bad = {"id": "d2", "name": "D2", "provider_id": "p1", "backend_model": "m",
               "capabilities": {"responses": "yes", "embeddings": False, "tools": False,
                                "structured_outputs": False}, "enabled": True}
        payload["deployments"].append(bad)
        error, providers, db = self._bootstrap(self._settings(payload))
        self.assertEqual(("bootstrap_invalid", 503), (error.code, error.status))
        self.assertEqual([], providers)
        # 回滚后空库可重新引导
        app = Application(db, self._settings(self._valid()))
        try:
            self.assertIsNone(app.bootstrap_error)
            self.assertEqual(1, len(app.registry.list_providers()))
        finally:
            app.store.close()

    def test_ensure_fixed_tiers_idempotent(self):
        db = self._db()
        store = Store(db); store.migrate()
        registry = Registry(store)
        registry.ensure_fixed_tiers()
        registry.ensure_fixed_tiers()
        levels = registry.list_service_levels()
        self.assertEqual(sorted(FIXED_TIERS), sorted(l["id"] for l in levels))
        store.close()


if __name__ == "__main__":
    unittest.main()
