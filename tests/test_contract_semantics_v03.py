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

    def test_forgotten_key_selects_finite_window_with_frozen_bounds(self):
        fixture = self.load(FIXTURES / "v0.3" / "idempotency-forgotten-key-options.json")
        decision = fixture["candidate_v0_3_decision"]
        self.assertEqual("C-finite-retention-scope", decision["selected"])
        self.assertTrue(decision["activation_allowed"])
        self.assertEqual(168, decision["guarantee_window_hours_min"])
        self.assertEqual(24, decision["safety_margin_hours"])
        self.assertEqual(144, decision["formula_deadline_hours_max"])
        self.assertEqual(24, decision["product_retry_recovery_deadline_hours_max"])
        self.assertLessEqual(
            decision["product_retry_recovery_deadline_hours_max"],
            decision["guarantee_window_hours_min"] - decision["safety_margin_hours"],
        )
        self.assertEqual(168, decision["terminal_digest_tombstone_retention_hours_min"])
        self.assertEqual(168, decision["invocation_terminal_view_retention_hours_min"])
        self.assertEqual(168, decision["canonical_response_recovery_hours_min"])
        self.assertTrue(any(option["new_mechanism"] for option in fixture["candidate_options"]))

    def test_v03_manifest_has_no_verified_endpoint(self):
        manifest = self.load(ROOT / "docs" / "contracts" / "compatibility-manifest-v0.3.json")
        self.assertTrue(manifest["activation"]["planned_or_conditional_fail_closed"])
        self.assertFalse(any(endpoint["support"] == "verified" for endpoint in manifest["data_plane_endpoints"]))
        self.assertTrue(manifest["idempotency_after_complete_deletion"]["activation_allowed"])

    def test_v03_manifest_has_one_complete_surface_and_no_fallback(self):
        manifest = self.load(ROOT / "docs" / "contracts" / "compatibility-manifest-v0.3.json")
        endpoints = {(item["method"], item["path"]) for item in manifest["data_plane_endpoints"]}
        self.assertEqual(
            {
                ("POST", "/v1/responses"),
                ("POST", "/v1/chat/completions"),
                ("POST", "/v1/embeddings"),
                ("GET", "/v1/models"),
                ("GET", "/v1/models/{service_level_id}"),
                ("GET", "/v1/invocations/{invocation_id}"),
                ("GET", "/v1/responses/{response_id}"),
            },
            endpoints,
        )
        self.assertEqual("single_v0_3_surface_no_fallback", manifest["surface_policy"])
        self.assertFalse(manifest["terminal_replay"]["http_200_invocation_view_allowed"])

    def test_registry_and_management_activation_requirements_are_explicit(self):
        manifest = self.load(ROOT / "docs" / "contracts" / "compatibility-manifest-v0.3.json")
        registry = manifest["service_level_registry"]
        self.assertEqual("llmtier", registry["authority"])
        self.assertEqual("exact_case_sensitive", registry["id_matching"])
        self.assertFalse(registry["aliases_allowed"])
        self.assertFalse(registry["cross_service_level_fallback_allowed"])
        management = manifest["management"]
        self.assertEqual("candidate_required", management["api_support"])
        self.assertEqual("candidate_required", management["admin_web_ui_support"])
        self.assertEqual("write_only_never_return_value", management["secret_policy"])

    def test_v03_data_plane_schema_definitions_exist(self):
        schema = self.load(ROOT / "docs" / "contracts" / "schemas" / "llmtier-data-plane-v0.3.schema.json")
        self.assertTrue(
            {
                "ResponsesRequest",
                "ResponsesResponse",
                "ChatCompletionRequest",
                "ChatCompletionResponse",
                "EmbeddingRequest",
                "EmbeddingResponse",
                "Model",
                "ModelList",
                "ErrorEnvelope",
                "TerminalErrorEnvelope",
                "ServiceLevelRegistryEntry",
            }.issubset(schema["$defs"])
        )

    def test_recovery_headers_and_readiness_schema_exist(self):
        recovery = self.load(ROOT / "docs" / "contracts" / "schemas" / "llmtier-recovery-v0.3.schema.json")
        headers = recovery["$defs"]["RecoveryHeaders"]
        self.assertEqual(["Location", "X-LLMTier-Invocation-Id"], headers["required"])
        invocation = self.load(ROOT / "docs" / "contracts" / "schemas" / "llmtier-contracts-v0.2.schema.json")["$defs"]["InvocationView"]
        self.assertTrue({"recovery_ready", "recovery_disposition", "retry_after_ms"}.issubset(invocation["required"]))

    def test_recovery_protocol_never_redispatches_duplicate(self):
        fixture = self.load(FIXTURES / "v0.3" / "recovery-protocol-fixtures.json")
        duplicate_cases = [case for case in fixture["cases"] if case["request"].get("same_key_and_digest")]
        self.assertTrue(duplicate_cases)
        self.assertTrue(all(case["expected"]["dispatch_count"] == 0 for case in duplicate_cases))

    def test_terminal_replay_never_returns_http_200_invocation_view(self):
        fixture = self.load(FIXTURES / "v0.3" / "recovery-protocol-fixtures.json")
        terminal = [
            case for case in fixture["cases"]
            if case["request"].get("existing_status") in {"Failed", "Cancelled", "UnknownOutcome"}
        ]
        self.assertEqual(3, len(terminal))
        for case in terminal:
            with self.subTest(case=case["id"]):
                self.assertEqual("TerminalErrorEnvelope", case["expected"]["body_schema"])
                self.assertNotEqual(200, case["expected"].get("http_status"))
                self.assertEqual(0, case["expected"]["dispatch_count"])
                self.assertEqual(["Location", "X-LLMTier-Invocation-Id"], case["expected"]["headers"])

    def test_scope_conflict_blocks_activation_without_creating_fallback(self):
        manifest = self.load(ROOT / "docs" / "contracts" / "compatibility-manifest-v0.3.json")
        review = manifest["scope_review"]
        self.assertEqual("pending_slinky_or_user_decision", review["resolution"])
        self.assertFalse(review["activation_allowed_while_unresolved"])
        self.assertFalse(review["parallel_or_fallback_surface_allowed"])


if __name__ == "__main__":
    unittest.main()
