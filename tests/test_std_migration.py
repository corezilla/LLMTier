import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "docs" / "std.lock.json"


class StdMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        cls.manifest_path = ROOT / cls.lock["source_manifest_path"]
        cls.manifest = json.loads(cls.manifest_path.read_text(encoding="utf-8"))
        cls.sources = cls.manifest["artifacts"]

    def test_draft17_lock_resolves_to_immutable_source_manifest(self):
        self.assertEqual("std-lock.v1", self.lock["schema_version"])
        self.assertEqual("0.1.0-draft.17", self.lock["std_version"])
        self.assertEqual("94c0262de35b5b989bba9f8d23f212af709c9dbf", self.lock["source_revision"])
        self.assertEqual("std-v0.1.0-draft.17", self.lock["source_tag"])
        self.assertTrue(self.manifest_path.is_file())
        self.assertEqual("software", self.lock["project_profile"])
        self.assertEqual(["management", "software"], self.lock["enabled_domains"])
        self.assertEqual(self.lock["std_version"], self.manifest["std_version"])
        self.assertEqual(self.lock["source_revision"], self.manifest["source_revision"])
        self.assertEqual(self.lock["source_tag"], self.manifest["source_tag"])

    def test_source_manifest_records_only_std_sources_with_sha256(self):
        self.assertEqual(71, len(self.sources))
        self.assertEqual(len(self.sources), len({item["path"] for item in self.sources}))
        for item in self.sources:
            self.assertIn(item["role"], {"example", "guidance", "schema", "template", "tool"})
            self.assertRegex(item["sha256"], r"^[a-f0-9]{64}$")

    def test_metadata_template_hashes_are_present_in_source_manifest(self):
        source_hashes = {item["path"]: item["sha256"] for item in self.sources}
        expected = {
            ROOT / "docs" / "30_subsystem_design" / "llmtier-service-design.metadata.json": "templates/design/design-definition.md",
            ROOT / "docs" / "00_management" / "std-tailoring.metadata.json": "templates/management/tailoring-manifest.md",
        }
        for metadata_path, source_path in expected.items():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertEqual("review", metadata["status"])
            self.assertEqual("0.1.0-draft.17", metadata["std_version"])
            self.assertIsNone(metadata["reviewed_commit"])
            self.assertEqual(source_hashes[source_path], metadata["template_sha256"])

    def test_llmtier_is_classified_as_one_service_not_a_system_or_workspace(self):
        design_metadata = json.loads(
            (ROOT / "docs" / "30_subsystem_design" / "llmtier-service-design.metadata.json").read_text(encoding="utf-8")
        )
        self.assertEqual("design.definition", design_metadata["document_type"])
        self.assertEqual("design.definition", design_metadata["template_id"])
        self.assertEqual("subsystem", design_metadata["design_level"])
        self.assertEqual(["software"], design_metadata["domain"])
        self.assertEqual("tailored", design_metadata["template_conformance"])
        self.assertEqual("std-tailoring", design_metadata["tailoring_ref"])
        self.assertEqual(
            "docs/30_subsystem_design/llmtier-service-design.md",
            design_metadata["source_path"],
        )

        tailoring = (ROOT / "docs" / "00_management" / "std-tailoring.md").read_text(encoding="utf-8")
        self.assertIn("单应用、单服务或单库", tailoring)
        self.assertIn("| LT-TL-003 | `design.system` | omit |", tailoring)
        self.assertIn("| LT-TL-013 | 多服务目录", tailoring)
        self.assertFalse((ROOT / "docs" / "design" / "llmtier-v0.3-system-design.md").exists())
        self.assertFalse((ROOT / "docs" / "management" / "std-tailoring-v0.1.md").exists())

    def test_service_design_uses_all_definition_sections_and_has_no_todos(self):
        path = ROOT / "docs" / "30_subsystem_design" / "llmtier-service-design.md"
        text = path.read_text(encoding="utf-8")
        headings = [line for line in text.splitlines() if line.startswith("## ")]
        for section in range(1, 15):
            self.assertTrue(any(line.startswith(f"## {section}.") for line in headings), section)
        self.assertNotIn("<!-- TODO -->", text)
        self.assertIn("| `src/llm_tier/` | 单服务 Python 当前实现基线 |", text)
        self.assertIn("| `tests/` | 单元、contract semantic 与迁移一致性测试 |", text)
        self.assertIn("| `docs/` | 设计、接口、QA、迁移和 provenance |", text)
        self.assertIn("不新建 `software/llmtier/`、`services/llmtier/`", text)

    def test_c1_interface_and_contract_candidates_preserve_machine_authority(self):
        candidates = {
            "piko-data-plane-control.md": "interfaces.control",
            "slinky-capacity-observation-control.md": "interfaces.control",
            "llmtier-management-control.md": "interfaces.control",
            "contracts/llmtier-v0.3-contract-specification.md": "contracts.specification",
        }
        root = ROOT / "docs" / "60_interfaces"
        for relative_path, template_id in candidates.items():
            path = root / relative_path
            metadata_path = path.with_suffix(".metadata.json")
            text = path.read_text(encoding="utf-8")
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertEqual(template_id, metadata["document_type"])
            self.assertEqual(template_id, metadata["template_id"])
            self.assertEqual("tailored", metadata["template_conformance"])
            self.assertEqual("std-tailoring", metadata["tailoring_ref"])
            self.assertEqual("draft", metadata["status"])
            self.assertIsNone(metadata["reviewed_commit"])
            self.assertIsNone(metadata["supersedes"])
            self.assertIn("openapi/llmtier-v0.3.openapi.json", text)
            self.assertNotIn("<!-- TODO -->", text)

        contract = (root / "contracts" / "llmtier-v0.3-contract-specification.md").read_text(encoding="utf-8")
        self.assertIn("唯一字段级 authority", contract)
        self.assertIn("overall.runtime_activation=false", contract)
        self.assertIn("不授权 runtime", contract)

        piko = (root / "piko-data-plane-control.md").read_text(encoding="utf-8")
        self.assertIn("Runtime → Piko → LLMTier", piko)
        self.assertIn("UnknownOutcome 只能 manual reconcile", piko)
        self.assertIn("不得 silent fallback", piko)

        slinky = (root / "slinky-capacity-observation-control.md").read_text(encoding="utf-8")
        self.assertIn("concurrent_invocation", slinky)
        self.assertIn("request_quota_remaining=null", slinky)
        self.assertIn("不等于 token/s、Agent Slot", slinky)

        management = (root / "llmtier-management-control.md").read_text(encoding="utf-8")
        self.assertIn("secret create/rotate 只写不读", management)
        self.assertIn("redispatch=false", management)
        self.assertIn("不构成 v0.3 Management compatibility", management)

    def test_c2_assurance_candidates_preserve_executable_authority_and_evidence_gaps(self):
        candidates = {
            ROOT / "docs" / "70_verification" / "plans" / "llmtier-v0.3-vv-plan.md": "assurance.vv-plan",
            ROOT / "docs" / "70_verification" / "specifications" / "llmtier-v0.3-contract-test-specification.md": "assurance.test-specification",
        }
        source_hashes = {item["path"]: item["sha256"] for item in self.sources}
        template_paths = {
            "assurance.vv-plan": "templates/assurance/verification-validation-plan.md",
            "assurance.test-specification": "templates/assurance/test-specification.md",
        }
        for path, template_id in candidates.items():
            text = path.read_text(encoding="utf-8")
            metadata = json.loads(path.with_suffix(".metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(template_id, metadata["document_type"])
            self.assertEqual(template_id, metadata["template_id"])
            self.assertEqual(source_hashes[template_paths[template_id]], metadata["template_sha256"])
            self.assertEqual("tailored", metadata["template_conformance"])
            self.assertEqual("std-tailoring", metadata["tailoring_ref"])
            self.assertEqual("draft", metadata["status"])
            self.assertIsNone(metadata["reviewed_commit"])
            self.assertIsNone(metadata["supersedes"])
            self.assertNotIn("<!-- TODO -->", text)
            self.assertIn("Runtime Activation", text)

        vv_plan = next(path for path, template_id in candidates.items() if template_id == "assurance.vv-plan")
        vv_text = vv_plan.read_text(encoding="utf-8")
        self.assertIn("NOT_RUN/BLOCKED", vv_text)
        self.assertIn("`tests/` 和 fixtures 是可执行 oracle", vv_text)

        test_spec = next(path for path, template_id in candidates.items() if template_id == "assurance.test-specification")
        spec_text = test_spec.read_text(encoding="utf-8")
        self.assertIn("CT-REC-002", spec_text)
        self.assertIn("tests/test_contract_semantics_v03.py", spec_text)
        self.assertIn("现有测试源码\n与 fixtures 仍是 executable oracle authority", spec_text)


if __name__ == "__main__":
    unittest.main()
