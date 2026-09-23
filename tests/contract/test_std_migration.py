import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class StdAndAuthorityTests(unittest.TestCase):
    def test_std_lock_and_source_manifest_resolve(self):
        lock = json.loads((ROOT / "docs" / "std.lock.json").read_text(encoding="utf-8"))
        manifest = json.loads((ROOT / lock["source_manifest_path"]).read_text(encoding="utf-8"))
        self.assertEqual("std-lock.v1", lock["schema_version"])
        self.assertEqual(lock["std_version"], manifest["std_version"])
        self.assertEqual(lock["source_revision"], manifest["source_revision"])
        self.assertEqual("software", lock["project_profile"])

    def test_llmtier_is_one_independent_software_system(self):
        metadata = json.loads((ROOT / "docs/20_system_design/llmtier-system-design.metadata.json").read_text(encoding="utf-8"))
        self.assertEqual("design.software-system", metadata["document_type"])
        self.assertEqual("design.software-system", metadata["template_id"])
        self.assertEqual("system", metadata["design_level"])
        self.assertEqual(["software"], metadata["domain"])
        self.assertIsNone(metadata["parent_document_id"])
        self.assertFalse((ROOT / "docs/30_subsystem_design").exists())

    def test_system_design_has_required_template_sections(self):
        text = (ROOT / "docs/20_system_design/llmtier-system-design.md").read_text(encoding="utf-8")
        headings = [line for line in text.splitlines() if line.startswith("## ")]
        for number in range(1, 18):
            self.assertTrue(any(line.startswith(f"## {number}.") for line in headings), number)
        for appendix in ("A", "B"):
            self.assertTrue(any(line.startswith(f"## 附录 {appendix}.") for line in headings), appendix)
        self.assertIn("design.software-system", text)
        self.assertIn("软件系统架构", text)
        self.assertIn("组成与职责", text)
        self.assertIn("不建立软件子系统", text)
        self.assertIn("docs/40_module_design/http-api-design.md", text)
        self.assertIn("docs/50_implementation_design/llmtier-runtime.isd.md", text)
        self.assertIn("assets/diagrams/llmtier-architecture-container.png", text)
        self.assertNotIn("<small>", text)

    def test_current_documents_and_metadata_versions_match(self):
        paths = [
            ROOT / "docs/10_requirements/llmtier-requirements.md",
            ROOT / "docs/10_requirements/llmtier-traceability.md",
            ROOT / "docs/20_system_design/llmtier-system-design.md",
            ROOT / "docs/40_module_design/llmtier-core-design.md",
            ROOT / "docs/40_module_design/llmtier-webui-design.md",
            ROOT / "docs/50_implementation_design/llmtier-runtime.isd.md",
            ROOT / "docs/60_interfaces/piko-data-plane-control.md",
            ROOT / "docs/60_interfaces/slinky-capacity-observation-control.md",
            ROOT / "docs/60_interfaces/llmtier-management-control.md",
            ROOT / "docs/60_interfaces/contracts/llmtier-contract-specification.md",
            ROOT / "docs/60_interfaces/contracts/llmtier-cross-system-finalization.md",
            ROOT / "docs/70_verification/plans/llmtier-vv-plan.md",
            ROOT / "docs/70_verification/specifications/llmtier-contract-test-specification.md",
            ROOT / "docs/80_operations/llmtier-release-and-operations.md",
        ]
        for path in paths:
            metadata = json.loads(path.with_name(path.stem + ".metadata.json").read_text(encoding="utf-8"))
            text = path.read_text(encoding="utf-8")
            self.assertIn(f"| Document Version | `{metadata['document_version']}` |", text, path)
            self.assertEqual("review", metadata["status"], path)
            self.assertIsNone(metadata["reviewed_commit"], path)
            self.assertIn(f"| Last Modified Date | `{metadata['last_modified_at']}` |", text, path)

    def test_current_authority_names_machine_artifacts_and_no_activation(self):
        contract = (ROOT / "docs/60_interfaces/contracts/llmtier-contract-specification.md").read_text(encoding="utf-8")
        self.assertIn("唯一字段级 authority", contract)
        self.assertIn("runtime_activation=false", contract)
        manifest = json.loads((ROOT / "interfaces/compatibility/compatibility-manifest-v0.3.json").read_text(encoding="utf-8"))
        self.assertFalse(manifest["overall"]["runtime_activation"])

    def test_current_prose_has_simplified_scope(self):
        docs = [
            ROOT / "docs/10_requirements/llmtier-requirements.md",
            ROOT / "docs/20_system_design/llmtier-system-design.md",
            ROOT / "docs/60_interfaces/piko-data-plane-control.md",
            ROOT / "docs/60_interfaces/slinky-capacity-observation-control.md",
        ]
        combined = "\n".join(path.read_text(encoding="utf-8") for path in docs)
        self.assertIn("无 Agent 会话状态", combined)
        self.assertIn("OpenAI-compatible", combined)
        self.assertIn("unknown", combined)
        self.assertIn("不执行工具", combined)
        self.assertIn("Cost", combined)
        self.assertIn("退出", combined)


if __name__ == "__main__":
    unittest.main()
