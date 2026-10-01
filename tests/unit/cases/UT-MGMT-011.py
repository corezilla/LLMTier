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














class AccountUsageGapTests(unittest.TestCase):
    """UT-MGMT-011: GET no-network / not_refreshed / credentials_missing / provider_api_error."""

    def setUp(self): self.fx = AppFixture()
    def tearDown(self): self.fx.close()

    def _minimax_provider(self):
        self.fx.app.registry.create_provider({
            "name": "MiniMax", "kind": "cloud", "endpoint": "https://api.minimaxi.com/v1",
            "secret_ref": "env:LLMTIER_UT_MINIMAX", "enabled": True, "usage": {"usage_provider": "minimax"},
        })
        return self.fx.app.registry.list_providers()[0]

    def test_latest_never_touches_network(self):
        provider = self._minimax_provider()
        with patch("management.account_usage._urlopen", side_effect=AssertionError("network call")):
            self.fx.app.account_usage.latest(provider["id"])

    def test_credentials_missing_snapshot(self):
        provider = self._minimax_provider()
        with patch.dict("os.environ", {}, clear=True):
            snapshot = self.fx.app.account_usage.latest(provider["id"])
        self.assertEqual((snapshot["status"], snapshot["source"]), ("unavailable", "credentials_missing"))

    def test_local_provider_not_refreshed(self):
        self.p, _ = self.fx.seed()
        snapshot = self.fx.app.account_usage.latest(self.p["id"])
        self.assertEqual((snapshot["source"], snapshot["status"]), ("store", "not_refreshed"))

    def test_refresh_requires_confirmation(self):
        provider = self._minimax_provider()
        with self.assertRaises(ApiError) as cm:
            self.fx.app.account_usage.refresh(provider["id"], False)
        self.assertEqual((cm.exception.status, cm.exception.code), (400, "confirmation_required"))

    def test_provider_api_error_is_unavailable_with_error_string(self):
        provider = self._minimax_provider()
        payload = {"base_resp": {"status_code": 1, "status_msg": "denied"}}
        with patch.dict("os.environ", {"LLMTIER_UT_MINIMAX": "k"}), patch("management.account_usage._urlopen", return_value=FakeResponse(payload)):
            snapshot = self.fx.app.account_usage.refresh(provider["id"], True)
        self.assertEqual((snapshot["status"], snapshot["source"]), ("unavailable", "provider_api_error"))
        self.assertEqual(snapshot["error"], "denied")
        self.assertNotIsInstance(snapshot["error"], type(None))


if __name__ == "__main__":
    unittest.main()
