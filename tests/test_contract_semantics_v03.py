import copy
import json
import unittest
from pathlib import Path

from tools.contract_semantic_validator_v03 import (
    validate_capacity_snapshot,
    validate_metadata,
    validate_projection,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "docs" / "contracts" / "fixtures"


class ContractSemanticsV03Tests(unittest.TestCase):
    def load(self, path: Path):
        return json.loads(path.read_text(encoding="utf-8"))

    def apply_capacity_mutation(self, snapshot, mutation):
        if "duplicate_group_id" in mutation:
            item = next(group for group in snapshot["capacity_groups"] if group["capacity_group_id"] == mutation["duplicate_group_id"])
            snapshot["capacity_groups"].append(copy.deepcopy(item))
        elif "duplicate_service_level_id" in mutation:
            item = next(level for level in snapshot["service_levels"] if level["service_level_id"] == mutation["duplicate_service_level_id"])
            snapshot["service_levels"].append(copy.deepcopy(item))
        elif "available_committed_concurrency" in mutation:
            item = next(group for group in snapshot["capacity_groups"] if group["capacity_group_id"] == mutation["group"])
            item["available_committed_concurrency"] = mutation["available_committed_concurrency"]
        elif "remove_group_ref" in mutation:
            item = next(level for level in snapshot["service_levels"] if level["service_level_id"] == mutation["level"])
            item["capacity_group_ids"].remove(mutation["remove_group_ref"])
        elif "valid_until" in mutation:
            snapshot["valid_until"] = mutation["valid_until"]
        elif "request_quota_remaining" in mutation:
            item = next(level for level in snapshot["service_levels"] if level["service_level_id"] == mutation["level"])
            item["request_quota_remaining"] = mutation["request_quota_remaining"]

    def test_capacity_negative_fixtures_execute_expected_result(self):
        base = self.load(FIXTURES / "v0.2" / "capacity-snapshot-example.json")
        fixture = self.load(FIXTURES / "v0.3" / "capacity-semantic-negative-fixtures.json")
        for case in fixture["cases"]:
            with self.subTest(case=case["id"]):
                snapshot = copy.deepcopy(base)
                self.apply_capacity_mutation(snapshot, case["mutation"])
                valid, code = validate_capacity_snapshot(snapshot)
                self.assertEqual(case["expected"]["snapshot_valid"], valid)
                if "requested_seats" in case:
                    allowed, code = validate_projection(snapshot, case["requested_seats"])
                    self.assertEqual(case["expected"]["projection_allowed"], allowed)
                self.assertEqual(case["expected"]["code"], code)

    def test_metadata_utf8_byte_fixtures_execute_expected_result(self):
        fixture = self.load(FIXTURES / "v0.3" / "metadata-utf8-byte-fixtures.json")
        for case in fixture["cases"]:
            with self.subTest(case=case["id"]):
                valid, code = validate_metadata({case["key"]: case["value"]})
                self.assertEqual(case["expected"]["valid"], valid)
                self.assertEqual(case["expected"].get("code"), code)

    def test_forgotten_key_has_no_silent_candidate_selection(self):
        fixture = self.load(FIXTURES / "v0.3" / "idempotency-forgotten-key-options.json")
        decision = fixture["candidate_v0_3_decision"]
        self.assertIsNone(decision["selected"])
        self.assertFalse(decision["activation_allowed"])
        self.assertTrue(any(option["new_mechanism"] for option in fixture["candidate_options"]))

    def test_v03_manifest_has_no_verified_endpoint(self):
        manifest = self.load(ROOT / "docs" / "contracts" / "compatibility-manifest-v0.3.json")
        self.assertTrue(manifest["activation"]["planned_or_conditional_fail_closed"])
        self.assertFalse(any(endpoint["support"] == "verified" for endpoint in manifest["endpoints"]))
        self.assertFalse(manifest["idempotency_after_complete_deletion"]["activation_allowed"])

    def test_recovery_protocol_never_redispatches_duplicate(self):
        fixture = self.load(FIXTURES / "v0.3" / "recovery-protocol-fixtures.json")
        duplicate_cases = [case for case in fixture["cases"] if case["request"].get("same_key_and_digest")]
        self.assertTrue(duplicate_cases)
        self.assertTrue(all(case["expected"]["dispatch_count"] == 0 for case in duplicate_cases))


if __name__ == "__main__":
    unittest.main()
