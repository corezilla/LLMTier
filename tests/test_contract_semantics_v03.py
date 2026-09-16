import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


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
        self.assertEqual("0.3-simplified-candidate.1", self.openapi["info"]["version"])
        self.assertEqual("0.3-simplified-candidate.1", self.manifest["manifest_version"])
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
        self.assert_valid("ResponsesRequest", {"model": "Worker", "input": tool["next_request_input"]})
        self.assertEqual("piko", tool["oracle"]["tool_executed_by"])
        self.assertFalse(tool["oracle"]["llmtier_history_state"])

    def test_stream_true_is_rejected_by_current_candidate(self):
        case = next(case for case in self.load("openai-surface-fixtures.json")["cases"] if case["id"] == "streaming-not-yet-frozen")
        self.assertTrue(list(self.validator("ResponsesRequest").iter_errors(case["request"])))
        self.assertFalse(case["oracle"]["fallback"])

    def test_embeddings_fixture_validates(self):
        case = next(case for case in self.load("openai-surface-fixtures.json")["cases"] if case["id"] == "embedding-success")
        self.assert_valid("EmbeddingRequest", case["request"])
        self.assert_valid("EmbeddingResponse", case["response"])
        self.assertEqual("slinky", case["oracle"]["index_owned_by"])

    def test_usage_measured_estimated_unknown(self):
        cases = self.load("usage-fixtures.json")["cases"]
        for case in cases:
            self.assert_valid("UsageRecord", case["record"])
        unknown = next(case for case in cases if case["id"] == "unknown")
        self.assertTrue(all(unknown["record"][key] is None for key in ("input_tokens", "output_tokens", "total_tokens", "cached_input_tokens")))
        invalid = next(case for case in cases if case["id"] == "invalid-unknown-zero")
        self.assertFalse(invalid["valid"])
        self.assertEqual("unknown_tokens_must_be_null", invalid["semantic_error"])

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
