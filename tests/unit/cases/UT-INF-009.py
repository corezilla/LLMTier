import threading
import time
import unittest
from unittest.mock import patch

import inference.routing as routing

from http_api.errors import ApiError
from tests.common.fakes import AppFixture




class RoutingAdmissionGapTests(unittest.TestCase):
    """UT-INF-004/009: queue-full / wait-timeout 429, RPM+interval throttle, snapshot shape, model codes."""

    def setUp(self): self.fx=AppFixture(); self.fx.seed("Worker"); self.router=self.fx.app.router
    def tearDown(self): self.fx.close()

    def test_queue_full_is_429_with_retry_after(self):
        self.router._queues["Worker"].extend([f"t{i}" for i in range(32)])
        with self.assertRaises(ApiError) as cm:
            with self.router.admit("Worker"): pass
        self.assertEqual((cm.exception.status,cm.exception.code),(429,"rate_limit_exceeded"))
        self.assertEqual(cm.exception.headers.get("Retry-After"),"30")

    def test_wait_timeout_is_429_with_retry_after(self):
        clock=[1_000_000.0]
        def jump(*_a, **_k): clock[0]+=31
        with patch.object(routing.time,"monotonic",side_effect=lambda: clock[0]), patch.object(self.router._condition,"wait",side_effect=jump):
            with self.router.admit("Worker"):
                with self.assertRaises(ApiError) as cm:
                    with self.router.admit("Worker"): pass
        self.assertEqual((cm.exception.status,cm.exception.code),(429,"rate_limit_exceeded"))
        self.assertEqual(cm.exception.headers.get("Retry-After"),"1")
        self.assertEqual(len(self.router._queues["Worker"]),0)

    def test_provider_min_interval_throttles(self):
        pid=self.fx.app.store.one("SELECT id FROM providers")[0]
        self.fx.app.store.connection().execute("UPDATE provider_usage_profiles SET min_request_interval_ms=250, requests_per_minute=0 WHERE provider_id=?",(pid,))
        self.assertEqual(self.router._provider_ready_in(pid,100.0),0.0)
        self.router._provider_last_dispatch[pid]=100.0
        self.assertGreater(self.router._provider_ready_in(pid,100.1),0.0)

    def test_provider_rpm_throttles(self):
        pid=self.fx.app.store.one("SELECT id FROM providers")[0]
        self.fx.app.store.connection().execute("UPDATE provider_usage_profiles SET min_request_interval_ms=0, requests_per_minute=1 WHERE provider_id=?",(pid,))
        self.router._provider_dispatches[pid].append(100.0)
        self.assertGreater(self.router._provider_ready_in(pid,100.1),0.0)
        self.assertEqual(self.router._provider_ready_in(pid,161.0),0.0)

    def test_snapshot_shape(self):
        _,d=self.fx.seed("Senior")
        snap=self.router.snapshot()
        self.assertIn("deployments",snap); self.assertIn("providers",snap); self.assertIn("queues",snap)
        entry=snap["deployments"][d["id"]]
        self.assertEqual(set(entry),{"running","max_concurrent"})
        self.assertEqual(entry["running"],0)

    def test_degraded_health_blocks_admission_503(self):
        self.fx.app.store.connection().execute("UPDATE deployments SET health='degraded'")
        with self.assertRaises(ApiError) as cm:
            with self.router.admit("Worker"): pass
        self.assertEqual((cm.exception.status,cm.exception.code),(503,"model_unavailable"))

    def test_unknown_health_blocks_admission_503(self):
        self.fx.app.store.connection().execute("UPDATE deployments SET health='unknown'")
        with self.assertRaises(ApiError) as cm:
            with self.router.admit("Worker"): pass
        self.assertEqual((cm.exception.status,cm.exception.code),(503,"model_unavailable"))
