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
