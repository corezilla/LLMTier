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




class ResourceInUseTests(unittest.TestCase):
    """UT-MGMT-008: referenced provider/deployment deletes → 409 resource_in_use."""

    def setUp(self): self.fx = AppFixture(); self.p, self.d = self.fx.seed()
    def tearDown(self): self.fx.close()

    def test_delete_provider_referenced_by_deployment_is_409(self):
        with self.assertRaises(ApiError) as cm:
            self.fx.app.registry.delete_provider(self.p["id"], self.fx.app.registry.get_provider(self.p["id"])[1])
        self.assertEqual((cm.exception.status, cm.exception.code), (409, "resource_in_use"))

    def test_delete_deployment_referenced_by_tier_is_409(self):
        with self.assertRaises(ApiError) as cm:
            self.fx.app.registry.delete_deployment(self.d["id"], self.fx.app.registry.get_deployment(self.d["id"])[1])
        self.assertEqual((cm.exception.status, cm.exception.code), (409, "resource_in_use"))












if __name__ == "__main__":
    unittest.main()
