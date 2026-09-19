import json
import unittest
from datetime import datetime, timedelta, timezone

from llmtier_v03.usage import UsageRecorder
from tests.unit.v03.fakes import AppFixture


class StatsEndpointTests(unittest.TestCase):
    def setUp(self):
        self.fx = AppFixture()
        self.provider, self.deployment = self.fx.seed(tier="Worker", backend_model="synthetic")
        self.admin = self.fx.app.admin
        self.admin = self.fx.app.admin
        self.now = datetime.now(timezone.utc)

    def tearDown(self):
        self.fx.close()

    def _record(self, principal, request_id, model, deployment, *, total, inp, out, status="measured", source="provider", cached=None, reasoning=None):
        recorder = UsageRecorder(self.fx.app.store)
        recorder.authorize_dispatch(principal, request_id, model, "/v1/responses")
        recorder.bind_backend(principal, request_id, deployment["provider_id"], deployment["id"])
        recorder.finish(principal, request_id, {
            "input_tokens": inp, "output_tokens": out, "total_tokens": total,
            "input_tokens_details": {"cached_tokens": cached or 0},
            "output_tokens_details": {"reasoning_tokens": reasoning or 0},
        })

    def test_stats_by_tier_aggregates_calls_and_tokens(self):
        self._record("p1", "r1", "Worker", self.deployment, total=20, inp=10, out=10)
        self._record("p1", "r2", "Worker", self.deployment, total=30, inp=15, out=15, cached=5, reasoning=3)
        self._record("p2", "r3", "Worker", self.deployment, total=40, inp=20, out=20)

        result = self.admin.stats("2000-01-01T00:00:00Z", "2999-12-31T23:59:59Z", "tier")
        self.assertEqual(result["group_by"], "tier")
        tiers = {row["tier"]: row for row in result["data"]}
        self.assertEqual(tiers["Worker"]["calls"], 3)
        self.assertEqual(tiers["Worker"]["total_tokens"], 90)
        self.assertEqual(tiers["Worker"]["input_tokens"], 45)
        self.assertEqual(tiers["Worker"]["output_tokens"], 45)
        self.assertEqual(tiers["Worker"]["cached_tokens"], 5)
        self.assertEqual(tiers["Worker"]["reasoning_tokens"], 3)
        self.assertEqual(tiers["Worker"]["measured_calls"], 3)

    def test_stats_by_deployment_includes_provider_metadata(self):
        self._record("p1", "r1", "Worker", self.deployment, total=12, inp=8, out=4)
        result = self.admin.stats("2000-01-01T00:00:00Z", "2999-12-31T23:59:59Z", "deployment")
        self.assertEqual(result["group_by"], "deployment")
        self.assertEqual(len(result["data"]), 1)
        row = result["data"][0]
        self.assertEqual(row["deployment_id"], self.deployment["id"])
        self.assertEqual(row["backend_model"], "synthetic")
        self.assertEqual(row["provider_kind"], "local")
        self.assertEqual(row["calls"], 1)
        self.assertEqual(row["total_tokens"], 12)

    def test_stats_aggregates_across_principals(self):
        self._record("p1", "r1", "Worker", self.deployment, total=10, inp=5, out=5)
        self._record("p2", "r2", "Worker", self.deployment, total=20, inp=10, out=10)
        result = self.admin.stats("2000-01-01T00:00:00Z", "2999-12-31T23:59:59Z", "tier")
        self.assertEqual(result["data"][0]["calls"], 2)
        self.assertEqual(result["data"][0]["total_tokens"], 30)

    def test_stats_rejects_invalid_group_by(self):
        from llmtier_v03.errors import ApiError
        with self.assertRaises(ApiError) as ctx:
            self.admin.stats("2000-01-01T00:00:00Z", "2999-12-31T23:59:59Z", "garbage")
        self.assertEqual(ctx.exception.code, "invalid_request")

    def test_stats_returns_empty_when_no_records(self):
        result = self.admin.stats("2000-01-01T00:00:00Z", "2999-12-31T23:59:59Z", "tier")
        self.assertEqual(result["data"], [])


if __name__ == "__main__":
    unittest.main()