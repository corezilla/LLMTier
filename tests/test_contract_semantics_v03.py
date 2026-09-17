import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from tools.contract_semantic_validator_v03 import (
    execute_usage_design_sequence,
    select_usage_replacement,
    validate_embedding_response,
    validate_sse_sequence,
    validate_usage_record,
    validate_usage_transition,
)


ROOT = Path(__file__).resolve().parents[1]
INTERFACES = ROOT / "interfaces"
OPENAPI_PATH = INTERFACES / "openapi" / "llmtier-v0.3.openapi.json"
MANIFEST_PATH = INTERFACES / "compatibility" / "compatibility-manifest-v0.3.json"
FIXTURES = INTERFACES / "vectors" / "v0.3"


class SimplifiedV03ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.openapi = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def load(self, name):
        return json.loads((FIXTURES / name).read_text(encoding="utf-8"))

    def validator(self, component):
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$ref": f"#/components/schemas/{component}",
            "components": self.openapi["components"],
        }
        return Draft202012Validator(schema)

    def assert_valid(self, component, instance):
        errors = list(self.validator(component).iter_errors(instance))
        self.assertEqual([], errors, [error.message for error in errors])

    def test_unique_simplified_machine_authority(self):
        self.assertEqual("3.1.0", self.openapi["openapi"])
        self.assertEqual("0.3-simplified-candidate.6", self.openapi["info"]["version"])
        self.assertEqual("0.3-simplified-candidate.6", self.manifest["manifest_version"])
        self.assertFalse(self.openapi["x-llmtier-runtime-activation"])
        self.assertFalse(self.manifest["overall"]["runtime_activation"])
        self.assertEqual("openapi/llmtier-v0.3.openapi.json", self.manifest["contract_authority"]["path"])

    def test_current_consumer_paths_are_minimal(self):
        paths = set(self.openapi["paths"])
        required = {
            "/v1/responses", "/v1/embeddings", "/v1/models", "/v1/models/{model}",
            "/tier/v1/usage", "/healthz", "/readyz",
        }
        self.assertTrue(required.issubset(paths))
        forbidden = {
            "/v1/invocations/{invocation_id}", "/v1/responses/{response_id}",
            "/tier/v1/capacity/snapshots/current", "/tier/v1/invocations",
            "/tier/v1/compatibility", "/tier/admin/v1/recovery-items",
            "/tier/admin/v1/clients", "/tier/admin/v1/sources",
        }
        self.assertTrue(forbidden.isdisjoint(paths))

    def test_no_removed_public_schema_or_header(self):
        text = OPENAPI_PATH.read_text(encoding="utf-8")
        for forbidden in [
            "SourceInstance", "X-Tier-Source-Instance-ID", "X-Tier-Invocation-ID",
            "Idempotency-Key", "InvocationView", "CapacitySnapshot", "CostEvidence",
            "RecoveryItem", "execution_released",
        ]:
            self.assertNotIn(forbidden, text)

    def test_responses_and_tool_loop_fixtures_validate(self):
        cases = {case["id"]: case for case in self.load("openai-surface-fixtures.json")["cases"]}
        text_case = cases["responses-text-success"]
        self.assert_valid("ResponsesRequest", text_case["request"])
        self.assert_valid("ResponsesResponse", text_case["response"])
        tool = cases["responses-tool-roundtrip"]
        self.assert_valid("ResponsesRequest", tool["first_request"])
        self.assert_valid("OutputFunctionCall", tool["first_output"])
        self.assert_valid("ResponsesRequest", {"model": "Worker", "input": tool["next_request_input"], "stream": True, "store": False})
        self.assert_valid("ResponsesRequest", {"model": "Worker", "input": tool["image_result_input"], "stream": True, "store": False})
        self.assert_valid("ResponsesRequest", cases["responses-assistant-history"]["request"])
        self.assert_valid("ResponsesRequest", cases["responses-assistant-refusal-history"]["request"])
        self.assert_valid("ResponsesRequest", cases["responses-reasoning-request"]["request"])
        self.assert_valid("ResponsesRequest", cases["exact-model-not-found"]["request"])
        self.assertEqual("piko", tool["oracle"]["tool_executed_by"])
        self.assertFalse(tool["oracle"]["llmtier_history_state"])

    def test_standard_responses_sse_matches_pinned_pi_subset(self):
        cases = {case["id"]: case for case in self.load("openai-surface-fixtures.json")["cases"]}
        for name in ("responses-sse-text-success", "responses-sse-function-call"):
            case = cases[name]
            self.assert_valid("ResponsesRequest", case["request"])
            for event in case["events"]:
                self.assert_valid("ResponseStreamEvent", event)
            self.assertIn(case["events"][-1]["type"], {"response.completed", "response.incomplete", "response.failed", "error"})
            self.assertEqual((True, None), validate_sse_sequence(case["events"]))
        tool = cases["responses-sse-function-call"]
        self.assert_valid("ResponsesRequest", {"model": "Worker", "input": tool["next_request_input"], "stream": True, "store": False})
        self.assertEqual("piko", tool["oracle"]["tool_executed_by"])
        incomplete = cases["responses-sse-missing-terminal"]
        for event in incomplete["events"]:
            self.assert_valid("ResponseStreamEvent", event)
        self.assertEqual((False, "stream_ended_without_terminal_event"), validate_sse_sequence(incomplete["events"]))
        mismatch = cases["responses-sse-terminal-status-mismatch"]
        for event in mismatch["events"]:
            self.assertTrue(list(self.validator("ResponseStreamEvent").iter_errors(event)))
        reasoning = cases["responses-sse-reasoning-refusal"]
        for event in reasoning["events"]:
            self.assert_valid("ResponseStreamEvent", event)
        self.assertEqual((True, None), validate_sse_sequence(reasoning["events"]))
        refusal = reasoning["events"][-2]["item"]["content"][0]
        self.assertEqual({"type": "refusal", "refusal": "Cannot comply"}, refusal)
        self.assert_valid("OutputRefusalContent", refusal)
        fake_refusal = json.loads(json.dumps(reasoning["events"]))
        fake_refusal[-2]["item"]["content"] = [{"type": "output_text", "text": "Cannot comply", "annotations": []}]
        self.assertEqual((False, "output_content_kind_mismatch"), validate_sse_sequence(fake_refusal))
        terminal_fake_refusal = json.loads(json.dumps(reasoning["events"]))
        terminal_fake_refusal[-1]["response"]["output"][1]["content"] = [
            {"type": "output_text", "text": "Cannot comply", "annotations": []}
        ]
        self.assertEqual(
            (False, "terminal_output_item_mismatch"),
            validate_sse_sequence(terminal_fake_refusal),
        )
        self.assertFalse(cases["responses-sse-text-success"]["oracle"]["fallback"])

        bad_delta_id = json.loads(json.dumps(cases["responses-sse-function-call"]["events"]))
        bad_delta_id[2]["item_id"] = "fc_unrelated"
        self.assertEqual((False, "delta_item_id_mismatch"), validate_sse_sequence(bad_delta_id))
        bad_terminal_id = json.loads(json.dumps(cases["responses-sse-function-call"]["events"]))
        bad_terminal_id[-1]["response"]["output"][0]["id"] = "fc_unrelated"
        self.assertEqual((False, "terminal_output_identity_mismatch"), validate_sse_sequence(bad_terminal_id))

    def test_responses_sse_is_same_endpoint_not_parallel_path(self):
        response = self.openapi["paths"]["/v1/responses"]["post"]["responses"]["200"]
        self.assertEqual({"text/event-stream"}, set(response["content"]))
        self.assertEqual("standard_sse", self.manifest["capabilities"][0]["mode"])
        self.assertEqual([], self.manifest["open_questions"])

    def test_embeddings_fixture_validates(self):
        case = next(case for case in self.load("openai-surface-fixtures.json")["cases"] if case["id"] == "embedding-success")
        self.assert_valid("EmbeddingRequest", case["request"])
        self.assert_valid("EmbeddingResponse", case["response"])
        self.assertEqual((True, None), validate_embedding_response(case["request"], case["response"], {2}))
        self.assertEqual("slinky", case["oracle"]["index_owned_by"])

    def test_embeddings_semantic_failures_are_rejected(self):
        case = next(case for case in self.load("openai-surface-fixtures.json")["cases"] if case["id"] == "embedding-success")
        count_mismatch = dict(case["response"])
        count_mismatch["data"] = count_mismatch["data"][:1]
        self.assertEqual((False, "embedding_count_mismatch"), validate_embedding_response(case["request"], count_mismatch, {2}))
        bad_index = dict(case["response"])
        bad_index["data"] = [dict(item) for item in case["response"]["data"]]
        bad_index["data"][1]["index"] = 0
        self.assertEqual((False, "embedding_index_mismatch"), validate_embedding_response(case["request"], bad_index, {2}))
        bad_dimension = dict(case["response"])
        bad_dimension["data"] = [dict(item) for item in case["response"]["data"]]
        bad_dimension["data"][1]["embedding"] = [0.3]
        self.assertEqual((False, "embedding_dimension_inconsistent"), validate_embedding_response(case["request"], bad_dimension, {2}))

        base64_case = next(case for case in self.load("openai-surface-fixtures.json")["cases"] if case["id"] == "embedding-base64-success")
        self.assert_valid("EmbeddingRequest", base64_case["request"])
        self.assert_valid("EmbeddingResponse", base64_case["response"])
        self.assertEqual((True, None), validate_embedding_response(base64_case["request"], base64_case["response"], {2}))
        representation_mismatch = json.loads(json.dumps(base64_case["response"]))
        representation_mismatch["data"][0]["embedding"] = [0.1, 0.2]
        self.assertEqual((False, "embedding_representation_mismatch"), validate_embedding_response(base64_case["request"], representation_mismatch, {2}))
        invalid_base64 = json.loads(json.dumps(base64_case["response"]))
        invalid_base64["data"][0]["embedding"] = "not-base64"
        self.assertEqual((False, "embedding_base64_invalid"), validate_embedding_response(base64_case["request"], invalid_base64, {2}))
        nonfinite_base64 = json.loads(json.dumps(base64_case["response"]))
        nonfinite_base64["data"][0]["embedding"] = "AADAf83MTD4="
        self.assertEqual((False, "embedding_value_not_finite"), validate_embedding_response(base64_case["request"], nonfinite_base64, {2}))

    def test_usage_measured_estimated_unknown(self):
        cases = self.load("usage-fixtures.json")["cases"]
        for case in cases:
            if case.get("valid") is True:
                self.assert_valid("UsageRecord", case["record"])
                self.assertEqual((True, None), validate_usage_record(case["record"]))
        unknown = next(case for case in cases if case["id"] == "unknown")
        self.assertTrue(all(unknown["record"][key] is None for key in ("input_tokens", "output_tokens", "total_tokens", "cached_input_tokens", "cache_write_tokens", "reasoning_tokens")))
        invalid = next(case for case in cases if case["id"] == "invalid-unknown-zero")
        self.assertTrue(list(self.validator("UsageRecord").iter_errors(invalid["record"])))
        self.assertEqual((False, "unknown_tokens_must_be_null"), validate_usage_record(invalid["record"]))

    def test_usage_revisions_replace_never_add(self):
        case = next(case for case in self.load("usage-fixtures.json")["cases"] if case["id"] == "replacement-not-addition")
        records = [
            {"request_id": item["request_id"], "record_version": item["record_version"]}
            for item in case["records"]
        ]
        self.assertEqual(2, select_usage_replacement(records)["record_version"])
        page = next(case for case in self.load("usage-fixtures.json")["cases"] if case["id"] == "stable-page")
        self.assert_valid("UsagePage", page["page"])
        previous = {"request_id": "req_05", "record_version": 2, "is_final": True, "measurement_status": "measured"}
        downgrade = {"request_id": "req_05", "record_version": 1, "is_final": False, "measurement_status": "estimated"}
        self.assertEqual((False, "record_version_not_increasing"), validate_usage_transition(previous, downgrade))

    def test_usage_subset_source_and_durability_oracles(self):
        cases = {case["id"]: case for case in self.load("usage-fixtures.json")["cases"]}
        for case_id in (
            "invalid-cached-input-subset",
            "invalid-reasoning-output-subset",
            "invalid-measured-source",
        ):
            case = cases[case_id]
            self.assertEqual((False, case["semantic_error"]), validate_usage_record(case["record"]))
        snapshot = cases["snapshot-freezes-record-versions"]
        self.assertEqual((True, None), execute_usage_design_sequence(snapshot["steps"]))
        durable = cases["durable-unknown-before-provider-dispatch"]
        self.assertEqual((True, None), execute_usage_design_sequence(durable["steps"]))
        dispatch_without_obligation = [
            {"action": "provider_dispatch"},
        ]
        self.assertEqual(
            (False, "dispatch_without_usage_obligation"),
            execute_usage_design_sequence(dispatch_without_obligation),
        )

    def test_cost_is_not_in_current_contract(self):
        text = OPENAPI_PATH.read_text(encoding="utf-8") + MANIFEST_PATH.read_text(encoding="utf-8")
        self.assertNotIn("CostEvidence", text)
        self.assertNotIn("amount_decimal", text)
        self.assertFalse(self.manifest["usage_policy"]["cost_supported"])

    def test_admin_surface_is_model_focused(self):
        paths = set(self.openapi["paths"])
        for resource in ("providers", "deployments", "service-levels"):
            self.assertIn(f"/tier/admin/v1/{resource}", paths)
        self.assertIn("/tier/admin/v1/probes", paths)
        self.assertIn("/tier/admin/v1/usage", paths)
        self.assertIn("/tier/admin/v1/audit", paths)
        self.assertIn("/tier/admin/v1/logs", paths)
        self.assertEqual(["主页", "添加模型", "运行状态", "用量", "审计", "日志"], self.manifest["admin_web_ui"]["pages"])
        excluded = set(self.manifest["admin_web_ui"]["excluded_pages"])
        self.assertEqual({"访问控制", "容量", "恢复", "费用", "调用方"}, excluded)

    def test_admin_secret_is_not_returned(self):
        schemas = self.openapi["components"]["schemas"]
        self.assertIn("secret_ref", schemas["ProviderWrite"]["properties"])
        self.assertNotIn("secret_ref", schemas["ProviderView"]["properties"])
        self.assertIn("has_secret", schemas["ProviderView"]["required"])
        case = self.load("admin-model-fixtures.json")["cases"][0]
        self.assert_valid("ProviderWrite", case["request"])
        self.assert_valid("ProviderView", case["response"])
        self.assertFalse(case["oracle"]["secret_value_returned"])
        cases = {case["id"]: case for case in self.load("admin-model-fixtures.json")["cases"]}
        self.assert_valid("ProviderPatch", cases["partial-provider-update"]["request"])
        self.assertTrue(list(self.validator("ProbeRequest").iter_errors(cases["probe-requires-confirmation"]["request"])))
        provider_path = self.openapi["paths"]["/tier/admin/v1/providers/{provider_id}"]
        for operation in ("patch", "delete"):
            refs = [parameter.get("$ref") for parameter in provider_path[operation]["parameters"]]
            self.assertIn("#/components/parameters/IfMatch", refs)
            self.assertIn("412", provider_path[operation]["responses"])

        log_case = cases["sanitized-operational-log-page"]
        self.assert_valid("LogPage", log_case["page"])
        serialized = json.dumps(log_case["page"], ensure_ascii=False).lower()
        for forbidden in log_case["oracle"]["forbidden_content_absent"]:
            self.assertNotIn(forbidden, serialized)
        logs = self.openapi["paths"]["/tier/admin/v1/logs"]["get"]
        self.assertEqual("listSanitizedLogs", logs["operationId"])
        self.assertEqual({"200", "400", "401", "403", "503"}, set(logs["responses"]))
        self.assertEqual(
            {"from", "to", "level", "module", "request_id", "cursor", "limit"},
            {parameter.get("name", parameter.get("$ref", "").rsplit("/", 1)[-1].replace("Page", "").lower()) for parameter in logs["parameters"]},
        )

    def test_stateless_boundary_and_minimal_extension_are_explicit(self):
        boundary = self.openapi["x-llmtier-architecture-boundary"]
        self.assertTrue(all(value is False for value in boundary.values()))
        fixture = {case["id"]: case for case in self.load("stateless-gateway-boundary-fixtures.json")["cases"]}
        extension = fixture["minimal-extension-justification"]
        self.assertEqual("/tier/v1/usage", extension["path"])
        self.assertEqual("token facts only", extension["scope"])

    def test_all_internal_openapi_refs_resolve(self):
        refs = []
        def walk(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    if key == "$ref": refs.append(child)
                    walk(child)
            elif isinstance(value, list):
                for child in value: walk(child)
        walk(self.openapi)
        for ref in refs:
            self.assertTrue(ref.startswith("#/"), ref)
            current = self.openapi
            for part in ref[2:].split("/"):
                current = current[part.replace("~1", "/").replace("~0", "~")]


if __name__ == "__main__":
    unittest.main()
