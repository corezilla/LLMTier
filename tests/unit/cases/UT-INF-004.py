from __future__ import annotations

import unittest

from http_api.errors import ApiError
from tests.common.fakes import AppFixture


class ModelTests(unittest.TestCase):
    def setUp(self): self.fx=AppFixture(); self.fx.seed(); self.models=self.fx.app.models
    def tearDown(self): self.fx.close()
    def test_list_object(self): self.assertEqual(self.models.list()["object"],"list")
    def test_list_has_seven_tiers(self): self.assertEqual(len(self.models.list()["data"]),7)
    def test_get_worker(self): self.assertEqual(self.models.get("Worker")["id"],"Worker")
    def test_owned_by(self): self.assertEqual(self.models.get("Worker")["owned_by"],"llmtier")
    def test_healthy_is_available(self): self.assertEqual(self.models.get("Worker")["availability"],"available")
    def test_unknown_is_degraded(self): self.fx.app.store.connection().execute("UPDATE deployments SET health='unknown'");self.assertEqual(self.models.get("Worker")["availability"],"degraded")
    def test_missing_model(self):
        with self.assertRaises(ApiError) as cm:self.models.get("Nope")
        self.assertEqual(cm.exception.code,"model_not_found")


import threading
import time
import unittest
from unittest.mock import patch

import inference.routing as routing

from http_api.errors import ApiError
from tests.common.fakes import AppFixture


class RoutingTests(unittest.TestCase):
    def setUp(self): self.fx=AppFixture(); self.fx.seed(); self.router=self.fx.app.router
    def tearDown(self): self.fx.close()
    def test_admits_healthy_candidate(self):
        with self.router.admit("Worker") as c:self.assertEqual(c.level_id,"Worker")
    def test_missing_model_is_404(self):
        with self.assertRaises(ApiError) as cm:
            with self.router.admit("missing"): pass
        self.assertEqual(cm.exception.status,404)
    def test_unhealthy_is_503(self):
        self.fx.app.store.connection().execute("UPDATE deployments SET health='unhealthy'")
        with self.assertRaises(ApiError) as cm:
            with self.router.admit("Worker"): pass
        self.assertEqual(cm.exception.status,503)
    def test_unknown_is_not_eligible(self):
        self.fx.app.store.connection().execute("UPDATE deployments SET health='unknown'")
        with self.assertRaises(ApiError):
            with self.router.admit("Worker"): pass
    def test_releases_inflight(self):
        with self.router.admit("Worker") as c:self.assertEqual(self.router._inflight[c.deployment_id],1)
        self.assertEqual(self.router._inflight[c.deployment_id],0)
    def test_second_request_waits_fifo(self):
        order=[]
        def run(name):
            with self.router.admit("Worker"): order.append(name); time.sleep(.02)
        a=threading.Thread(target=run,args=("a",));b=threading.Thread(target=run,args=("b",));a.start();time.sleep(.005);b.start();a.join();b.join();self.assertEqual(order,["a","b"])
    def test_does_not_cross_tier(self):
        with self.assertRaises(ApiError):
            with self.router.admit("Senior"): pass


