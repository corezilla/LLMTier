from __future__ import annotations

import http.client
import io
import json
import tempfile
import unittest
import urllib.error
from email.message import Message
from pathlib import Path
from unittest.mock import patch

from http_api.errors import ApiError
from inference.providers.openai import OpenAIProvider


class FakeResponse:
    def __init__(self, body, content_type="application/json", status=200):
        self.body = body if isinstance(body, bytes) else body.encode()
        self.status = status
        self.headers = Message()
        self.headers["Content-Type"] = content_type

    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self): return self.body


class OpenAIProviderTests(unittest.TestCase):

    def test_incomplete_terminal_is_preserved(self):
        response={"status":"incomplete","output":[],"usage":{"input_tokens":1,"output_tokens":2,"total_tokens":3},"error":None,"incomplete_details":{"reason":"max_output_tokens"}}
        stream=f"event: response.incomplete\ndata: {json.dumps({'type':'response.incomplete','response':response})}\n\ndata: [DONE]\n\n"
        with patch("urllib.request.urlopen",return_value=FakeResponse(stream,"text/event-stream")):
            result=OpenAIProvider("https://provider.example",None).complete("m",{"input":"x"})
        self.assertEqual(result.status,"incomplete")
        self.assertEqual(result.incomplete_details,{"reason":"max_output_tokens"})

    def test_duplicate_terminal_is_rejected(self):
        response={"status":"completed","output":[],"usage":None}
        event=f"event: response.completed\ndata: {json.dumps({'type':'response.completed','response':response})}\n\n"
        with patch("urllib.request.urlopen",return_value=FakeResponse(event+event,"text/event-stream")):
            with self.assertRaises(ApiError) as caught:
                OpenAIProvider("https://provider.example",None).complete("m",{"input":"x"})
        self.assertEqual(caught.exception.code,"provider_contract_error")

    def test_terminal_event_status_mismatch_is_rejected(self):
        response={"status":"incomplete","output":[],"usage":None}
        stream=f"event: response.completed\ndata: {json.dumps({'type':'response.completed','response':response})}\n\n"
        with patch("urllib.request.urlopen",return_value=FakeResponse(stream,"text/event-stream")):
            with self.assertRaises(ApiError) as caught:
                OpenAIProvider("https://provider.example",None).complete("m",{"input":"x"})
        self.assertEqual(caught.exception.code,"provider_contract_error")





import tempfile
import threading
import time
import unittest

from management.registry import Registry
from inference.routing import Router
from util.store import Store


class RuntimeSnapshotTests(unittest.TestCase):
    def test_snapshot_reports_configured_concurrency_without_inventing_usage(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(f"{directory}/state.sqlite3")
            store.migrate()
            registry = Registry(store)
            with store.transaction(True) as connection:
                connection.execute(
                    "INSERT INTO providers VALUES(?,?,?,?,?,?,?)",
                    ("provider_one", "Provider One", "local", "http://127.0.0.1:9000/v1", None, 1, 1),
                )
                connection.execute(
                    "INSERT INTO deployments VALUES(?,?,?,?,?,?,?,?)",
                    ("deployment_one", "Deployment One", "provider_one", "model-one", "{}", 1, "healthy", 1),
                )
                connection.execute(
                    "INSERT INTO deployment_runtime_profiles(deployment_id,max_in_flight) VALUES(?,?)",
                    ("deployment_one", 3),
                )
                connection.execute(
                    "INSERT INTO provider_usage_profiles(provider_id,usage_provider,max_concurrent_requests,min_request_interval_ms,requests_per_minute) VALUES(?,?,?,?,?)",
                    ("provider_one", "local", 2, 250, 20),
                )
            router = Router(registry)
            snapshot = router.snapshot()
            self.assertEqual(snapshot["deployments"]["deployment_one"], {"running": 0, "max_concurrent": 3})
            self.assertEqual(snapshot["providers"]["provider_one"], {"running": 0, "max_concurrent": 2, "min_request_interval_ms": 250, "requests_per_minute": 20})
            self.assertEqual(snapshot["queues"], {})

    def test_provider_account_concurrency_limits_multiple_deployments_together(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(f"{directory}/state.sqlite3"); store.migrate(); registry = Registry(store)
            with store.transaction(True) as connection:
                connection.execute("INSERT INTO providers VALUES(?,?,?,?,?,?,?)", ("p", "P", "local", "http://127.0.0.1:9/v1", None, 1, 1))
                connection.execute("INSERT INTO provider_usage_profiles(provider_id,usage_provider,max_concurrent_requests) VALUES(?,?,?)", ("p", "local", 1))
                connection.execute("INSERT INTO service_levels VALUES(?,?,?,?)", ("Worker", 1, "{}", 1))
                for ordinal in range(2):
                    did = f"d{ordinal}"
                    connection.execute("INSERT INTO deployments VALUES(?,?,?,?,?,?,?,?)", (did, did, "p", did, "{}", 1, "healthy", 1))
                    connection.execute("INSERT INTO deployment_runtime_profiles(deployment_id,max_in_flight) VALUES(?,?)", (did, 1))
                    connection.execute("INSERT INTO service_level_deployments VALUES(?,?,?)", ("Worker", did, ordinal))
            router = Router(registry); entered = threading.Event()
            def second():
                with router.admit("Worker"):
                    entered.set()
            with router.admit("Worker"):
                thread = threading.Thread(target=second); thread.start(); time.sleep(0.05)
                self.assertFalse(entered.is_set())
                self.assertEqual(router.snapshot()["providers"]["p"]["running"], 1)
            thread.join(1)
            self.assertTrue(entered.is_set())
            store.close()


if __name__ == "__main__":
    unittest.main()


import unittest

from http_api.errors import ApiError
from tests.common.fakes import AppFixture


START="2000-01-01T00:00:00Z";END="2100-01-01T00:00:00Z"


class UsageTests(unittest.TestCase):
    def setUp(self):self.fx=AppFixture();self.u=self.fx.app.usage
    def tearDown(self):self.fx.close()
    def record(self,rid="r1",usage=None):self.u.authorize_dispatch("p",rid,"Worker","/v1/responses");self.u.finish("p",rid,usage)
    def test_unknown_created_before_finish(self):
        self.u.authorize_dispatch("p","r","Worker","/v1/responses");self.assertEqual(self.u.page("p",None,since=START,until=END)["data"][0]["measurement_status"],"unknown")
    def test_measured_replaces_head(self):
        self.record(usage={"input_tokens":2,"output_tokens":3,"total_tokens":5});self.assertEqual(self.u.page("p",None,since=START,until=END)["data"][0]["record_version"],2)
    def test_versions_are_immutable(self):
        self.record(usage={"input_tokens":2,"output_tokens":3,"total_tokens":5});self.assertEqual(self.fx.app.store.one("SELECT count(*) FROM usage_record_versions")[0],2)
    def test_unknown_values_are_null(self):
        self.record();r=self.u.page("p",None,since=START,until=END)["data"][0];self.assertIsNone(r["total_tokens"])
    def test_principal_scope(self):
        self.record();self.assertEqual(self.u.page("other",None,since=START,until=END)["data"],[])
    def test_admin_sees_all(self):
        self.record();self.assertEqual(len(self.u.page("admin",None,admin=True,since=START,until=END)["data"]),1)
    def test_half_open_boundary_is_temporal_not_lexicographic(self):
        # S2 regression: recorded_at is ms-precision ("...T00:00:00.500Z") while a
        # caller's `to` may be second-precision ("...T00:00:00Z"). A lexicographic
        # string compare wrongly includes the same-second record ('.' < 'Z'); the
        # [from,to) contract must exclude it. The record instant equals the second
        # boundary, so `to`=that second excludes it and `from`=that second includes it.
        self.u.authorize_dispatch("p","r","Worker","/v1/responses");self.u.finish("p","r",{"input_tokens":1,"output_tokens":1,"total_tokens":2})
        with self.fx.app.store.transaction(True) as conn:
            conn.execute("UPDATE usage_obligations SET recorded_at='2026-01-01T00:00:00.500Z' WHERE principal_id='p' AND request_id='r'")
            conn.execute("UPDATE usage_record_versions SET recorded_at='2026-01-01T00:00:00.500Z' WHERE principal_id='p' AND request_id='r'")
        self.assertEqual(self.u.page("p",None,since="2025-12-31T00:00:00Z",until="2026-01-01T00:00:00Z")["data"],[])
        self.assertEqual(len(self.u.page("p",None,since="2026-01-01T00:00:00Z",until="2026-01-02T00:00:00Z")["data"]),1)
    def test_record_provider_request_id_updates_binding(self):
        provider,deployment=self.fx.seed();self.u.authorize_dispatch("p","r","Worker","/v1/responses");self.u.bind_backend("p","r",provider["id"],deployment["id"]);self.u.record_provider_request_id("p","r","up-1");self.assertEqual(self.fx.app.store.one("SELECT provider_request_id FROM provider_request_bindings WHERE principal_id='p' AND request_id='r'")[0],"up-1")
    def test_record_provider_request_id_null_is_noop(self):
        provider,deployment=self.fx.seed();self.u.authorize_dispatch("p","r","Worker","/v1/responses");self.u.bind_backend("p","r",provider["id"],deployment["id"]);self.u.record_provider_request_id("p","r",None);self.assertIsNone(self.fx.app.store.one("SELECT provider_request_id FROM provider_request_bindings WHERE principal_id='p' AND request_id='r'")[0])
