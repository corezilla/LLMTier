import tempfile
import unittest

from llmtier_v03.registry import Registry
from llmtier_v03.routing import Router
from llmtier_v03.store import Store


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
            router = Router(registry)
            snapshot = router.snapshot()
            self.assertEqual(snapshot["deployments"]["deployment_one"], {"running": 0, "max_concurrent": 3})
            self.assertEqual(snapshot["queues"], {})


if __name__ == "__main__":
    unittest.main()
