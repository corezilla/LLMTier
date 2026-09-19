import json
import unittest
from unittest.mock import patch

from .fakes import AppFixture


class FakeResponse:
    def __init__(self, payload): self.payload = json.dumps(payload).encode()
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self): return self.payload


class AccountUsageTests(unittest.TestCase):
    def setUp(self):
        self.fx = AppFixture()

    def tearDown(self):
        self.fx.close()

    def test_provider_usage_profile_is_safe_and_round_trips(self):
        provider, etag = self.fx.app.registry.create_provider({
            "name": "MiniMax", "kind": "cloud", "endpoint": "https://api.minimaxi.com/v1",
            "secret_ref": "env:MINIMAX_API_KEY", "enabled": True,
            "usage": {"usage_provider": "minimax", "max_concurrent_requests": 3, "min_request_interval_ms": 250, "requests_per_minute": 20},
        })
        self.assertEqual(provider["usage"]["usage_provider"], "minimax")
        self.assertEqual(provider["usage"]["max_concurrent_requests"], 3)
        self.assertNotIn("usage_api_key_ref", json.dumps(provider))
        updated, _ = self.fx.app.registry.update_provider(provider["id"], {"usage": {"requests_per_minute": 30}}, etag)
        self.assertEqual(updated["usage"]["max_concurrent_requests"], 3)
        self.assertEqual(updated["usage"]["requests_per_minute"], 30)

    def test_minimax_refresh_reuses_provider_api_key_and_persists_safe_snapshot(self):
        provider, _ = self.fx.app.registry.create_provider({
            "name": "MiniMax", "kind": "cloud", "endpoint": "https://api.minimaxi.com/v1",
            "secret_ref": "env:MINIMAX_API_KEY", "enabled": True, "usage": {"usage_provider": "minimax"},
        })
        payload = {"base_resp": {"status_code": 0}, "model_remains": [{"model_name": "general", "current_interval_remaining_percent": 87.5, "current_weekly_remaining_percent": 80}]}
        with patch.dict("os.environ", {"MINIMAX_API_KEY": "test-key"}), patch("llmtier_v03.account_usage._urlopen", return_value=FakeResponse(payload)) as refresh:
            value = self.fx.app.account_usage.refresh(provider["id"], True)
        request = refresh.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
        self.assertIsNone(request.get_header("Cookie"))
        self.assertEqual(self.fx.app.account_usage.latest(provider["id"])["windows"][0]["percent"], 12.5)

    def test_request_usage_is_attributed_to_selected_provider(self):
        provider, deployment = self.fx.seed()
        self.fx.app.usage.authorize_dispatch("client", "req", "Worker", "/v1/responses")
        self.fx.app.usage.bind_backend("client", "req", provider["id"], deployment["id"])
        self.fx.app.usage.finish("client", "req", {"input_tokens": 2, "output_tokens": 1, "total_tokens": 3})
        view, _ = self.fx.app.registry.get_provider(provider["id"])
        self.assertEqual(view["request_usage"], {"calls": 1, "input_tokens": 2, "output_tokens": 1, "total_tokens": 3})

    def test_local_usage_is_unlimited(self):
        provider, _ = self.fx.seed()
        value = self.fx.app.account_usage.refresh(provider["id"], True)
        self.assertEqual(value["status"], "unlimited")

    def test_minimax_uses_official_token_plan_api_key_without_cookie(self):
        payload = {"base_resp": {"status_code": 0}, "model_remains": [{"model_name": "general", "current_interval_remaining_percent": 90, "current_weekly_remaining_percent": 80}]}
        seen = {}
        def open_request(request, timeout):
            seen["url"], seen["headers"], seen["timeout"] = request.full_url, dict(request.header_items()), timeout
            return FakeResponse(payload)
        provider, _ = self.fx.app.registry.create_provider({"name": "MiniMax 2", "kind": "cloud", "endpoint": "https://api.minimaxi.com/v1", "secret_ref": "env:MINI_KEY", "enabled": True, "usage": {"usage_provider": "minimax"}})
        with patch.dict("os.environ", {"MINI_KEY": "key"}), patch("llmtier_v03.account_usage._urlopen", side_effect=open_request):
            result = self.fx.app.account_usage.refresh(provider["id"], True)
        self.assertEqual(seen["url"], "https://www.minimaxi.com/v1/token_plan/remains")
        self.assertEqual(seen["headers"]["Authorization"], "Bearer key")
        self.assertNotIn("Cookie", seen["headers"])
        self.assertEqual(result["status"], "ok")
