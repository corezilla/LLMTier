import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTERFACES = ROOT / "interfaces"
FIXTURES = INTERFACES / "vectors" / "v0.2"


class ContractFixtureTests(unittest.TestCase):
    def load(self, path: Path):
        return json.loads(path.read_text(encoding="utf-8"))

    def test_manifest_does_not_advertise_unverified_surface(self):
        manifest = self.load(INTERFACES / "compatibility" / "compatibility-manifest-v0.2.json")
        self.assertTrue(manifest["activation"]["planned_or_conditional_fail_closed"])
        self.assertFalse(any(endpoint["support"] == "verified" for endpoint in manifest["endpoints"]))

    def test_capacity_snapshot_group_membership_is_bidirectional(self):
        snapshot = self.load(FIXTURES / "capacity-snapshot-example.json")
        groups = {item["capacity_group_id"]: item for item in snapshot["capacity_groups"]}
        levels = {item["service_level_id"]: item for item in snapshot["service_levels"]}

        for level_id, level in levels.items():
            for group_id in level["capacity_group_ids"]:
                self.assertIn(group_id, groups)
                self.assertIn(level_id, groups[group_id]["member_service_level_ids"])
        for group_id, group in groups.items():
            self.assertLessEqual(group["available_committed_concurrency"], group["committed_concurrency"])
            for level_id in group["member_service_level_ids"]:
                self.assertIn(level_id, levels)
                self.assertIn(group_id, levels[level_id]["capacity_group_ids"])

    def test_required_positive_and_negative_fixture_classes_exist(self):
        capacity = self.load(FIXTURES / "capacity-projection-fixtures.json")
        ids = {case["id"] for case in capacity["cases"]}
        self.assertEqual(
            {
                "shared-group-positive",
                "shared-group-overallocated-negative",
                "overlapping-groups-negative",
                "burst-not-committed-negative",
                "client-quota-negative",
                "snapshot-expired-negative",
            },
            ids,
        )
        self.assertTrue(any(case["expected"]["valid"] for case in capacity["cases"]))
        self.assertTrue(any(not case["expected"]["valid"] for case in capacity["cases"]))

        idempotency = self.load(FIXTURES / "idempotency-recovery-fixtures.json")
        invocation = self.load(FIXTURES / "invocation-recovery-fixtures.json")
        self.assertIn("concurrent-duplicate-same-digest", {case["id"] for case in idempotency["cases"]})
        self.assertIn("crash-after-dispatch-before-ack", {case["id"] for case in idempotency["cases"]})
        self.assertIn("same-source-new-instance-can-recover", {case["id"] for case in invocation["cases"]})
        self.assertIn("unknown-outcome-is-not-not-found", {case["id"] for case in invocation["cases"]})


if __name__ == "__main__":
    unittest.main()
