import copy
import json
import re
import unittest
import warnings
from pathlib import Path

from jsonschema import Draft202012Validator, RefResolver

from tools.contract_semantic_validator_v03 import (
    validate_capacity_snapshot,
    validate_metadata,
    validate_projection,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "docs" / "contracts"
FIXTURES = CONTRACTS / "fixtures"
OPENAPI_PATH = CONTRACTS / "openapi" / "llmtier-v0.3.openapi.json"
MANIFEST_PATH = CONTRACTS / "compatibility-manifest-v0.3.json"


class ContractSemanticsV03Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.openapi = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            cls.resolver = RefResolver.from_schema(cls.openapi)

    def load(self, path: Path):
        return json.loads(path.read_text(encoding="utf-8"))

    def resolve_pointer(self, document, ref):
        self.assertTrue(ref.startswith("#/"), ref)
        value = document
        for raw in ref[2:].split("/"):
            token = raw.replace("~1", "/").replace("~0", "~")
            self.assertIn(token, value, ref)
            value = value[token]
        return value

    def walk_refs(self, value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "$ref":
                    yield item
                yield from self.walk_refs(item)
        elif isinstance(value, list):
            for item in value:
                yield from self.walk_refs(item)

    def validate_component(self, name, instance):
        schema = self.openapi["components"]["schemas"][name]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            errors = list(Draft202012Validator(schema, resolver=self.resolver).iter_errors(instance))
        return errors

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

    def test_openapi_version_and_every_internal_ref_resolves(self):
        self.assertEqual("3.1.0", self.openapi["openapi"])
        self.assertFalse(self.openapi["x-runtime-activation"])
        refs = list(self.walk_refs(self.openapi))
        self.assertGreater(len(refs), 100)
        for ref in refs:
            with self.subTest(ref=ref):
                self.resolve_pointer(self.openapi, ref)

    def test_every_component_schema_is_valid_draft_2020_12(self):
        for name, schema in self.openapi["components"]["schemas"].items():
            with self.subTest(schema=name):
                Draft202012Validator.check_schema(schema)

    def test_manifest_has_one_openapi_authority_and_refs_resolve(self):
        self.assertNotIn("schema_bundles", self.manifest)
        authority = self.manifest["contract_authority"]
        self.assertEqual("openapi-3.1-json", authority["format"])
        self.assertEqual("openapi/llmtier-v0.3.openapi.json", authority["path"])
        self.assertFalse(authority["runtime_activation"])

        def iter_contract_refs(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key.endswith("_ref") and isinstance(item, str) and "#" in item:
                        yield item
                    elif key.endswith("_refs") and isinstance(item, list):
                        yield from (entry for entry in item if isinstance(entry, str) and "#" in entry)
                    yield from iter_contract_refs(item)
            elif isinstance(value, list):
                for item in value:
                    yield from iter_contract_refs(item)

        refs = list(iter_contract_refs(self.manifest))
        self.assertTrue(refs)
        for ref in refs:
            path, fragment = ref.split("#", 1)
            with self.subTest(ref=ref):
                self.assertEqual(authority["path"], path)
                self.resolve_pointer(self.openapi, f"#{fragment}")

    def test_data_plane_positive_and_negative_fixtures(self):
        fixture = self.load(FIXTURES / "v0.3" / "data-plane-openapi-fixtures.json")
        self.assertTrue(any(case["valid"] for case in fixture["cases"]))
        self.assertTrue(any(not case["valid"] for case in fixture["cases"]))
        for case in fixture["cases"]:
            with self.subTest(case=case["id"]):
                errors = self.validate_component(case["schema"], case["body"])
                self.assertEqual(case["valid"], not errors, [error.message for error in errors])

    def test_required_data_plane_fields_and_deprecated_chat_field(self):
        responses = self.openapi["components"]["schemas"]["ResponsesRequest"]["properties"]
        chat = self.openapi["components"]["schemas"]["ChatCompletionRequest"]["properties"]
        self.assertIn("store", responses)
        self.assertIn("max_completion_tokens", chat)
        self.assertIn("stream_options", chat)
        self.assertNotIn("max_tokens", chat)

    def test_create_replay_and_retrieve_use_same_canonical_response_schema(self):
        create_ref = self.openapi["paths"]["/v1/responses"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        retrieve_ref = self.openapi["paths"]["/v1/responses/{response_id}"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        manifest_ref = self.manifest["data_plane_endpoints"][0]["success_response_schema_ref"].split("#", 1)[1]
        self.assertEqual("#/components/schemas/ResponsesResponse", create_ref)
        self.assertEqual(create_ref, retrieve_ref)
        self.assertEqual(create_ref, f"#{manifest_ref}")
        schema = self.resolve_pointer(self.openapi, create_ref)
        self.assertEqual("integer", schema["properties"]["created_at"]["type"])
        self.assertNotIn("invocation_id", schema["properties"])
        self.assertNotIn("retained_until", schema["properties"])

    def test_sse_sequence_fixtures(self):
        fixture = self.load(FIXTURES / "v0.3" / "sse-event-sequences.json")
        for case in fixture["cases"]:
            with self.subTest(case=case["id"]):
                events = case["events"]
                if case["protocol"] == "responses":
                    terminals = [i for i, event in enumerate(events) if event["type"] in {"response.completed", "error"}]
                    valid = bool(events) and events[0]["type"] == "response.created"
                    valid = valid and len(terminals) == 1 and terminals[0] == len(events) - 1
                    valid = valid and [event["sequence_number"] for event in events] == list(range(len(events)))
                else:
                    terminals = [i for i, event in enumerate(events) if event["type"] in {"[DONE]", "error"}]
                    valid = len(terminals) == 1 and terminals[0] == len(events) - 1
                    if valid and events[-1]["type"] == "[DONE]":
                        valid = any(event.get("finish_reason") for event in events[:-1])
                    if valid and case.get("include_usage"):
                        valid = any("usage" in event for event in events[:-1])
                self.assertEqual(case["valid"], valid)

    def test_recovery_protocol_active_and_terminal_contract(self):
        fixture = self.load(FIXTURES / "v0.3" / "recovery-protocol-fixtures.json")
        duplicate_cases = [case for case in fixture["cases"] if case["request"].get("same_key_and_digest")]
        self.assertTrue(duplicate_cases)
        self.assertTrue(all(case["expected"]["dispatch_count"] == 0 for case in duplicate_cases))
        active = next(case for case in fixture["cases"] if case["id"] == "nonstream-lost-response-retry-active")
        self.assertEqual(["Location", "X-Tier-Invocation-ID", "Retry-After"], active["expected"]["headers"])
        terminal = [case for case in fixture["cases"] if case["request"].get("existing_status") in {"Failed", "Cancelled", "UnknownOutcome"}]
        self.assertEqual({502, 409, 503}, {case["expected"]["http_status"] for case in terminal})
        for case in terminal:
            self.assertEqual("TerminalErrorEnvelope", case["expected"]["body_schema"])
            self.assertEqual(["Location", "X-Tier-Invocation-ID"], case["expected"]["headers"])

        responses = self.openapi["components"]["responses"]
        self.assertEqual(
            ["Location", "X-Tier-Invocation-ID", "Retry-After"],
            list(responses["ActiveReplay"]["headers"]),
        )
        for name in ["TerminalOrConflict", "TerminalFailure", "UnknownOutcome"]:
            self.assertEqual(["Location", "X-Tier-Invocation-ID"], list(responses[name]["headers"]), name)
            self.assertTrue(all(header["$ref"].startswith("#/components/headers/") for header in responses[name]["headers"].values()))

    def test_invocation_accepted_excludes_unknown_outcome(self):
        accepted = self.openapi["components"]["schemas"]["InvocationAccepted"]
        self.assertEqual(["Pending", "Queued", "Running"], accepted["properties"]["status"]["enum"])
        self.assertNotIn("UnknownOutcome", accepted["properties"]["status"]["enum"])

    def test_data_plane_observation_and_management_endpoint_coverage(self):
        data_plane = {
            "/v1/responses", "/v1/chat/completions", "/v1/embeddings", "/v1/models",
            "/v1/models/{service_level_id}", "/v1/invocations/{invocation_id}", "/v1/responses/{response_id}",
        }
        observation = {
            "/tier/v1/readiness", "/tier/v1/service-levels", "/tier/v1/service-levels/{service_level_id}",
            "/tier/v1/capacity/snapshots/current", "/tier/v1/invocations", "/tier/v1/invocations/{invocation_id}",
            "/tier/v1/usage/summary", "/tier/v1/compatibility",
        }
        management = {
            "/tier/admin/v1/providers", "/tier/admin/v1/providers/{provider_id}",
            "/tier/admin/v1/accounts", "/tier/admin/v1/accounts/{account_id}", "/tier/admin/v1/accounts/{account_id}/secret",
            "/tier/admin/v1/deployments", "/tier/admin/v1/deployments/{deployment_id}",
            "/tier/admin/v1/service-levels", "/tier/admin/v1/service-levels/{service_level_id}", "/tier/admin/v1/registry/publish",
            "/tier/admin/v1/pools", "/tier/admin/v1/pools/{pool_id}",
            "/tier/admin/v1/clients", "/tier/admin/v1/clients/{client_id}", "/tier/admin/v1/clients/{client_id}/credentials",
            "/tier/admin/v1/sources", "/tier/admin/v1/sources/{source_id}",
            "/tier/admin/v1/entitlements", "/tier/admin/v1/entitlements/{entitlement_id}",
            "/tier/admin/v1/discovery/jobs", "/tier/admin/v1/probe/jobs", "/tier/admin/v1/jobs/{job_id}",
            "/tier/admin/v1/capacity", "/tier/admin/v1/usage", "/tier/admin/v1/audit", "/tier/admin/v1/recovery/actions",
        }
        paths = set(self.openapi["paths"])
        self.assertTrue(data_plane.issubset(paths))
        self.assertTrue(observation.issubset(paths))
        self.assertTrue(management.issubset(paths))

    def test_observation_lists_have_pagination_and_gets_have_etag_304(self):
        for path in ["/tier/v1/service-levels", "/tier/v1/invocations"]:
            parameters = self.openapi["paths"][path]["get"]["parameters"]
            refs = {item.get("$ref") for item in parameters}
            self.assertIn("#/components/parameters/Limit", refs)
            self.assertIn("#/components/parameters/Cursor", refs)
        for path in [
            "/tier/v1/readiness", "/tier/v1/service-levels", "/tier/v1/service-levels/{service_level_id}",
            "/tier/v1/capacity/snapshots/current", "/tier/v1/invocations", "/tier/v1/invocations/{invocation_id}",
            "/tier/v1/usage/summary", "/tier/v1/compatibility",
        ]:
            responses = self.openapi["paths"][path]["get"]["responses"]
            self.assertIn("304", responses, path)
            self.assertIn("ETag", responses["200"]["headers"], path)

    def test_management_create_update_async_and_secret_contracts(self):
        for path, item in self.openapi["paths"].items():
            if not path.startswith("/tier/admin/v1"):
                continue
            if "post" in item:
                refs = {param.get("$ref") for param in item["post"].get("parameters", [])}
                self.assertIn("#/components/parameters/IdempotencyKey", refs, path)
            if "patch" in item:
                operation = item["patch"]
                refs = {param.get("$ref") for param in operation.get("parameters", [])}
                self.assertIn("#/components/parameters/IfMatch", refs, path)
                schema_ref = operation["requestBody"]["content"]["application/json"]["schema"]["$ref"]
                schema = self.resolve_pointer(self.openapi, schema_ref)
                self.assertIn("expected_version", schema["required"], path)
        account = self.openapi["components"]["schemas"]["AccountView"]
        self.assertNotIn("secret", account["properties"])
        one_time = self.openapi["components"]["schemas"]["OneTimeCredential"]["properties"]["secret"]
        self.assertTrue(one_time["x-one-time-return"])
        for path in ["/tier/admin/v1/discovery/jobs", "/tier/admin/v1/probe/jobs", "/tier/admin/v1/registry/publish", "/tier/admin/v1/recovery/actions"]:
            self.assertIn("202", self.openapi["paths"][path]["post"]["responses"])

    def test_only_authoritative_path_and_header_names_exist(self):
        files = [
            MANIFEST_PATH,
            OPENAPI_PATH,
            CONTRACTS / "piko-data-plane-contract-v0.3.md",
            CONTRACTS / "slinky-capacity-observation-contract-v0.3.md",
            CONTRACTS / "llmtier-management-contract-v0.3.md",
            ROOT / "docs" / "design" / "llmtier-v0.3-design-review.md",
            ROOT / "docs" / "qa" / "llm-tier-contract-qa-v0.3.md",
            FIXTURES / "v0.3" / "recovery-protocol-fixtures.json",
        ]
        text = "\n".join(path.read_text(encoding="utf-8") for path in files)
        for forbidden in ["X-Client-Request-Id", "X-LLMTier-Invocation-Id", "x-tier-invocation-id"]:
            self.assertNotIn(forbidden, text)
        self.assertIsNone(re.search(r"(?<!/tier)/admin/v1", text))
        self.assertIn("X-Tier-Client-Request-ID", text)
        self.assertIn("X-Tier-Invocation-ID", text)

    def test_activation_is_unambiguously_false(self):
        self.assertEqual("candidate", self.manifest["overall"]["contract_status"])
        self.assertFalse(self.manifest["overall"]["runtime_activation"])
        self.assertFalse(self.manifest["contract_authority"]["runtime_activation"])
        self.assertTrue(all(not item["runtime_activation"] for item in self.manifest["capability_activation"]))
        policy = self.manifest["idempotency_after_complete_deletion"]
        self.assertTrue(policy["policy_selected"])
        self.assertFalse(policy["runtime_activation"])
        self.assertNotIn("activation_allowed", policy)

    def test_forgotten_key_policy_selected_but_not_active(self):
        decision = self.load(FIXTURES / "v0.3" / "idempotency-forgotten-key-options.json")["candidate_v0_3_decision"]
        self.assertEqual("C-finite-retention-scope", decision["selected"])
        self.assertTrue(decision["policy_selected"])
        self.assertFalse(decision["runtime_activation"])
        self.assertEqual(168, decision["guarantee_window_hours_min"])
        self.assertEqual(24, decision["safety_margin_hours"])
        self.assertLessEqual(decision["product_retry_recovery_deadline_hours_max"], decision["formula_deadline_hours_max"])

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

    def test_scope_conflict_blocks_activation_without_fallback(self):
        review = self.manifest["scope_review"]
        self.assertEqual("pending_slinky_or_user_decision", review["resolution"])
        self.assertFalse(review["activation_allowed_while_unresolved"])
        self.assertFalse(review["parallel_or_fallback_surface_allowed"])


if __name__ == "__main__":
    unittest.main()
