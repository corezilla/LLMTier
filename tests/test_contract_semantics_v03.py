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
SYSTEM_DESIGN_PATH = ROOT / "docs" / "design" / "llmtier-v0.3-system-design.md"
AUTHORIZATION_SCOPE_FIXTURE_PATH = FIXTURES / "v0.3" / "authorization-scope-fixtures.json"


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

    def test_openapi_has_no_duplicate_keys_and_operation_ids_are_unique(self):
        def reject_duplicates(pairs):
            value = {}
            for key, item in pairs:
                if key in value:
                    raise ValueError(f"duplicate JSON key: {key}")
                value[key] = item
            return value

        json.loads(OPENAPI_PATH.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates)
        operation_ids = [operation["operationId"] for item in self.openapi["paths"].values() for method, operation in item.items() if method in {"get", "post", "patch", "delete"}]
        self.assertEqual(len(operation_ids), len(set(operation_ids)))

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

    def test_required_data_plane_fields_and_streaming_fail_closed(self):
        responses = self.openapi["components"]["schemas"]["ResponsesRequest"]["properties"]
        self.assertIn("store", responses)
        self.assertEqual(False, responses["stream"]["const"])

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

    def test_v03_authority_has_no_chat_or_sse(self):
        self.assertNotIn("/v1/chat/completions", self.openapi["paths"])
        text = json.dumps(self.openapi)
        self.assertNotIn("text/event-stream", text)
        self.assertFalse(any("Chat" in name or "SSE" in name or "StreamError" in name for name in self.openapi["components"]["schemas"]))
        deferred = self.load(FIXTURES / "v0.3" / "deferred-surface-fail-closed.json")
        self.assertEqual({"unsupported_endpoint", "unsupported_feature"}, {case["expected_code"] for case in deferred["cases"]})

    def test_manifest_current_and_deferred_scopes_are_disjoint(self):
        current = {(entry["method"], entry["path"]) for entry in self.manifest["data_plane_endpoints"]}
        self.assertEqual({
            ("POST", "/v1/responses"), ("POST", "/v1/embeddings"),
            ("GET", "/v1/models"), ("GET", "/v1/models/{service_level_id}"),
            ("GET", "/v1/invocations/{invocation_id}"), ("GET", "/v1/responses/{response_id}"),
        }, current)
        self.assertEqual(["nonstream"], self.manifest["data_plane_endpoints"][0]["modes"])
        self.assertTrue(all(entry["support"] == "v0.3_required_active_candidate" for entry in self.manifest["data_plane_endpoints"]))
        self.assertNotIn("chat_completions", {item["name"] for item in self.manifest["capability_activation"]})
        self.assertEqual(False, self.openapi["x-runtime-activation"])

    def test_recovery_protocol_active_and_terminal_contract(self):
        fixture = self.load(FIXTURES / "v0.3" / "recovery-protocol-fixtures.json")
        duplicate_cases = [case for case in fixture["cases"] if case["request"].get("existing_status")]
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

        no_id = next(case for case in fixture["cases"] if case["id"] == "nonstream-response-headers-lost-no-invocation-id")
        self.assertFalse(no_id["request"]["invocation_id_known"])
        self.assertTrue(no_id["request"]["same_key_and_digest"])
        self.assertEqual("replay_same_post", no_id["expected"]["recovery_action"])
        self.assertEqual("/v1/responses", no_id["expected"]["endpoint"])
        self.assertFalse(no_id["expected"]["new_attempt"])
        self.assertFalse(no_id["expected"]["new_recovery_path"])
        self.assertFalse(no_id["expected"]["new_idempotency_key"])
        self.assertEqual(0, no_id["expected"]["additional_dispatch_if_record_exists"])
        self.assertFalse(no_id["expected"]["unknown_outcome_redispatch"])

    def test_authorization_scope_fixtures_preserve_three_surface_boundaries(self):
        cases = {case["id"]: case for case in self.load(AUTHORIZATION_SCOPE_FIXTURE_PATH)["cases"]}
        positive = cases["observation-same-client-authorized-multiple-sources-positive"]
        self.assertTrue(positive["expected"]["allowed"])
        self.assertEqual(["source-a1", "source-a2"], positive["expected"]["visible_source_ids"])
        self.assertFalse(positive["expected"]["source_filter_is_authorization_namespace"])

        unauthorized = cases["observation-unauthorized-source-negative"]
        cross_client = cases["observation-cross-client-negative"]
        self.assertFalse(unauthorized["expected"]["allowed"])
        self.assertFalse(cross_client["expected"]["allowed"])

        recovery = cases["data-plane-recovery-remains-source-scoped"]
        self.assertEqual(["authenticated_client_id", "canonical_source_id"], recovery["expected"]["namespace"])
        self.assertFalse(recovery["expected"]["source_instance_is_namespace"])

    def test_invocation_accepted_excludes_unknown_outcome(self):
        accepted = self.openapi["components"]["schemas"]["InvocationAccepted"]
        self.assertEqual(["Pending", "Queued", "Running"], accepted["properties"]["status"]["enum"])
        self.assertNotIn("UnknownOutcome", accepted["properties"]["status"]["enum"])

    def test_system_design_uses_canonical_invocation_status_names(self):
        design = SYSTEM_DESIGN_PATH.read_text(encoding="utf-8")
        invocation_statuses = set(self.openapi["components"]["schemas"]["InvocationStatus"]["enum"])
        self.assertEqual(
            {"Pending", "Queued", "Running", "Succeeded", "Failed", "Cancelled", "UnknownOutcome"},
            invocation_statuses,
        )
        self.assertNotRegex(design, r"\bCompleted\b")
        self.assertIn("| Succeeded | 原 endpoint canonical `200` body", design)
        self.assertIn("terminal 为 Succeeded、Failed、Cancelled、", design)

    def test_system_design_keeps_registry_etags_and_retention_scopes_distinct(self):
        design = SYSTEM_DESIGN_PATH.read_text(encoding="utf-8")
        self.assertIn("ETag 各自校验本 resource representation", design)
        self.assertIn("live capacity/usage", design)
        self.assertIn("canonical Response 在冻结的\n168h recovery window 内仍可恢复", design)
        self.assertIn("短于任一下限的配置无效并阻断 activation", design)

    def test_data_plane_observation_and_management_endpoint_coverage(self):
        data_plane = {
            "/v1/responses", "/v1/embeddings", "/v1/models",
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
            "/tier/admin/v1/source-instances", "/tier/admin/v1/source-instances/{source_instance_id}",
            "/tier/admin/v1/capacity-groups", "/tier/admin/v1/capacity-groups/{capacity_group_id}",
            "/tier/admin/v1/entitlements", "/tier/admin/v1/entitlements/{entitlement_id}",
            "/tier/admin/v1/discovery/jobs", "/tier/admin/v1/probe/jobs", "/tier/admin/v1/jobs", "/tier/admin/v1/jobs/{job_id}",
            "/tier/admin/v1/capacity", "/tier/admin/v1/usage", "/tier/admin/v1/audit",
            "/tier/admin/v1/recovery-items", "/tier/admin/v1/recovery-items/{recovery_item_id}", "/tier/admin/v1/recovery-items/{recovery_item_id}/actions",
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

    def test_observation_dtos_and_filter_dimensions_are_complete(self):
        readiness = self.openapi["components"]["schemas"]["ReadinessView"]
        self.assertTrue({"status", "tier_instance_id", "tier_version", "observation_api_ready", "visible_service_levels", "snapshot_version", "next_refresh_at"}.issubset(readiness["required"]))
        level = self.openapi["components"]["schemas"]["ServiceLevelView"]
        self.assertTrue({"kind", "capabilities", "context", "modalities", "compatibility_manifest_ref"}.issubset(level["required"]))
        compatibility = self.openapi["components"]["schemas"]["CompatibilityEndpoint"]
        self.assertTrue({"method", "path", "supported_fields", "unsupported_fields", "streaming", "response_schema_version", "error_contract_version", "sdk_matrix"}.issubset(compatibility["required"]))

        invocation_params = {item.get("name") for item in self.openapi["paths"]["/tier/v1/invocations"]["get"]["parameters"] if "name" in item}
        self.assertTrue({"status", "service_level_id", "source_id", "source_instance_id", "from", "to", "client_request_id"}.issubset(invocation_params))
        usage_params = {item.get("name") for item in self.openapi["paths"]["/tier/v1/usage/summary"]["get"]["parameters"] if "name" in item}
        self.assertTrue({"from", "to", "interval", "group_by", "source_id", "source_instance_id", "service_level_id", "endpoint", "status"}.issubset(usage_params))
        observation_error = self.openapi["components"]["responses"]["ObservationError"]
        self.assertEqual(["source_error", "contract_mismatch"], observation_error["x-error-codes"])

    def test_models_304_has_if_none_match_precondition(self):
        for path in ["/v1/models", "/v1/models/{service_level_id}"]:
            operation = self.openapi["paths"][path]["get"]
            self.assertIn("304", operation["responses"])
            self.assertIn("#/components/parameters/IfNoneMatch", {item.get("$ref") for item in operation["parameters"]})

    def test_observation_and_admin_aggregate_fixtures(self):
        fixture = self.load(FIXTURES / "v0.3" / "observation-management-openapi-fixtures.json")
        for case in fixture["cases"]:
            with self.subTest(case=case["id"]):
                errors = self.validate_component(case["schema"], case["body"])
                self.assertEqual(case["valid"], not errors, [error.message for error in errors])

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
        for path in ["/tier/admin/v1/discovery/jobs", "/tier/admin/v1/probe/jobs", "/tier/admin/v1/registry/publish", "/tier/admin/v1/recovery-items/{recovery_item_id}/actions"]:
            self.assertIn("202", self.openapi["paths"][path]["post"]["responses"])

    def test_management_etag_documentation_matches_openapi(self):
        for path, item in self.openapi["paths"].items():
            if not path.startswith("/tier/admin/v1") or "get" not in item:
                continue
            operation = item["get"]
            refs = {parameter.get("$ref") for parameter in operation.get("parameters", [])}
            self.assertIn("#/components/parameters/IfNoneMatch", refs, path)
            self.assertIn("304", operation["responses"], path)
            self.assertIn("ETag", operation["responses"]["200"]["headers"], path)

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

    def test_scope_resolution_is_frozen_without_fallback(self):
        review = self.manifest["scope_review"]
        self.assertEqual("B", review["decision"])
        self.assertEqual("decided_by_slinky_S-20260906-2f9539048493", review["resolution"])
        self.assertEqual(["chat_completions", "responses_sse", "chat_sse", "all_streaming_replay_and_event_contracts"], review["v0.4_deferred_not_implemented"])
        self.assertFalse(review["parallel_or_fallback_surface_allowed"])


if __name__ == "__main__":
    unittest.main()
