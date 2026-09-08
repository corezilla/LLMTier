import json
import subprocess
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

    def test_draft18_lock_resolves_to_immutable_source_manifest(self):
        self.assertEqual("std-lock.v1", self.lock["schema_version"])
        self.assertEqual("0.1.0-draft.18", self.lock["std_version"])
        self.assertEqual("9841083c4d8d0ed1556bdc413d77b4567ac696b4", self.lock["source_revision"])
        self.assertEqual("std-v0.1.0-draft.18", self.lock["source_tag"])
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
            self.assertEqual("accepted", metadata["status"])
            self.assertEqual("0.1.0-draft.18", metadata["std_version"])
            self.assertEqual("962e8003712738d2cb4e3a0a38173a9fd2bdd0a1", metadata["reviewed_commit"])
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
            "piko-data-plane-control.md": ("interfaces.control", "962e8003712738d2cb4e3a0a38173a9fd2bdd0a1", "docs/99_reference/contracts/piko-data-plane-contract-v0.3.md"),
            "slinky-capacity-observation-control.md": ("interfaces.control", "e1f9b796368ec5f358e466c7e6299cc16b1bf181", "docs/99_reference/contracts/slinky-capacity-observation-contract-v0.3.md"),
            "llmtier-management-control.md": ("interfaces.control", "962e8003712738d2cb4e3a0a38173a9fd2bdd0a1", "docs/99_reference/contracts/llmtier-management-contract-v0.3.md"),
            "contracts/llmtier-v0.3-contract-specification.md": ("contracts.specification", "962e8003712738d2cb4e3a0a38173a9fd2bdd0a1", None),
        }
        root = ROOT / "docs" / "60_interfaces"
        for relative_path, (template_id, reviewed_commit, supersedes) in candidates.items():
            path = root / relative_path
            metadata_path = path.with_suffix(".metadata.json")
            text = path.read_text(encoding="utf-8")
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertEqual(template_id, metadata["document_type"])
            self.assertEqual(template_id, metadata["template_id"])
            self.assertEqual("tailored", metadata["template_conformance"])
            self.assertEqual("std-tailoring", metadata["tailoring_ref"])
            self.assertEqual("accepted", metadata["status"])
            self.assertEqual(reviewed_commit, metadata["reviewed_commit"])
            self.assertEqual(supersedes, metadata["supersedes"])
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
            self.assertEqual("accepted", metadata["status"])
            self.assertEqual("962e8003712738d2cb4e3a0a38173a9fd2bdd0a1", metadata["reviewed_commit"])
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

    def test_c3_requirements_and_traceability_keep_project_authority_and_honest_status(self):
        root = ROOT / "docs" / "10_requirements"
        candidates = {
            root / "llmtier-v0.3-requirements.md": "requirements.specification",
            root / "llmtier-v0.3-traceability.md": "requirements.traceability",
        }
        template_paths = {
            "requirements.specification": "templates/requirements/requirements-specification.md",
            "requirements.traceability": "templates/requirements/traceability-matrix.md",
        }
        source_hashes = {item["path"]: item["sha256"] for item in self.sources}
        for path, template_id in candidates.items():
            text = path.read_text(encoding="utf-8")
            metadata = json.loads(path.with_suffix(".metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(template_id, metadata["document_type"])
            self.assertEqual(source_hashes[template_paths[template_id]], metadata["template_sha256"])
            self.assertEqual("tailored", metadata["template_conformance"])
            self.assertEqual("std-tailoring", metadata["tailoring_ref"])
            self.assertEqual("accepted", metadata["status"])
            self.assertEqual("962e8003712738d2cb4e3a0a38173a9fd2bdd0a1", metadata["reviewed_commit"])
            self.assertNotIn("<!-- TODO -->", text)

        requirements = (root / "llmtier-v0.3-requirements.md").read_text(encoding="utf-8")
        self.assertIn("LT-FUN-001", requirements)
        self.assertIn("Piko 的 Agent Runtime/adapter 需求仅作为", requirements)
        self.assertIn("Runtime Activation", requirements)

        traceability = (root / "llmtier-v0.3-traceability.md").read_text(encoding="utf-8")
        self.assertIn("blocked-runtime", traceability)
        self.assertIn("open-decision/not-run", traceability)
        self.assertIn("不迁入本仓库", traceability)

    def test_c4_operations_candidate_is_not_a_runtime_or_adr_claim(self):
        path = ROOT / "docs" / "80_operations" / "llmtier-v0.3-release-and-operations.md"
        text = path.read_text(encoding="utf-8")
        metadata = json.loads(path.with_suffix(".metadata.json").read_text(encoding="utf-8"))
        source_hashes = {item["path"]: item["sha256"] for item in self.sources}
        self.assertEqual("operations.release", metadata["document_type"])
        self.assertEqual("operations.release", metadata["template_id"])
        self.assertEqual(
            source_hashes["templates/operations/release-and-operations.md"],
            metadata["template_sha256"],
        )
        self.assertEqual("accepted", metadata["status"])
        self.assertEqual("962e8003712738d2cb4e3a0a38173a9fd2bdd0a1", metadata["reviewed_commit"])
        self.assertIsNone(metadata["supersedes"])
        self.assertNotIn("<!-- TODO -->", text)
        self.assertIn("不是 release approval 或 runtime runbook", text)
        self.assertIn("overall.runtime_activation=false", text)
        self.assertIn("NOT_RUN/BLOCKED", text)
        self.assertIn("不创建 retrospective ADR", (ROOT / "docs" / "91_reviews" / "llmtier-std-c4-operations-review.md").read_text(encoding="utf-8"))

    def test_c5_promotion_is_atomic_and_does_not_activate_runtime(self):
        readiness = (ROOT / "docs" / "98_migration" / "canonical-promotion-readiness.md").read_text(encoding="utf-8")
        packet = (ROOT / "docs" / "91_reviews" / "llmtier-std-c5-canonical-promotion-review.md").read_text(encoding="utf-8")
        decision = json.loads(
            (ROOT / "docs" / "91_reviews" / "llmtier-std-c5-canonical-promotion-review.review-decision.json").read_text(encoding="utf-8")
        )
        self.assertIn("READY_FOR_COMMIT", readiness)
        self.assertIn("11 份实质 STD 文档实例、5 份 C0-C4 review packet/terminal decision", readiness)
        self.assertIn("Runtime Activation 始终保持独立", readiness)
        self.assertIn("当前原子 promotion candidate", packet)
        self.assertEqual("PENDING", decision["verdict"])
        self.assertFalse(decision["runtime_activation_requested"])
        self.assertEqual([], decision["reviewers"])
        self.assertIsNone(decision["decided_at"])
        self.assertIn("RAG publication 仍不在本 scope", packet)

        mapping = (ROOT / "docs" / "98_migration" / "legacy-v03-scope-mapping.md").read_text(encoding="utf-8")
        for legacy in (
            "docs/99_reference/design/llmtier-v0.3-design-review.md",
            "docs/99_reference/contracts/piko-data-plane-contract-v0.3.md",
            "docs/99_reference/contracts/slinky-capacity-observation-contract-v0.3.md",
            "docs/99_reference/contracts/llmtier-management-contract-v0.3.md",
            "docs/99_reference/verification/llm-tier-contract-qa-v0.3.md",
        ):
            self.assertIn(legacy, mapping)
        self.assertIn("S-20260907-45938693e578", mapping)
        self.assertIn("P-20260907-e009921eda0a", mapping)
        self.assertIn("residual=none", mapping)

        owner = (ROOT / "docs" / "98_migration" / "evidence" / "c5-owner-verdicts.txt").read_text(encoding="utf-8")
        self.assertIn("C0 Foundation", owner)
        self.assertIn("C1 Interface + Contract", owner)
        self.assertIn("C2 Assurance", owner)
        self.assertIn("C3 Requirements + Traceability", owner)
        self.assertIn("C4 Decisions + Operations", owner)
        self.assertIn("C1 terminal decision time", owner)
        self.assertIn("STD reviewer role", owner)
        self.assertIn("C1 uses decision_commit=e1f9b796368ec5f358e466c7e6299cc16b1bf181", owner)
        self.assertIn("No reviewed_commit or decision_commit may be filled with a commit that predates", owner)

        substantive = [
            ROOT / "docs" / "00_management" / "std-tailoring.metadata.json",
            ROOT / "docs" / "10_requirements" / "llmtier-v0.3-requirements.metadata.json",
            ROOT / "docs" / "10_requirements" / "llmtier-v0.3-traceability.metadata.json",
            ROOT / "docs" / "30_subsystem_design" / "llmtier-service-design.metadata.json",
            ROOT / "docs" / "60_interfaces" / "piko-data-plane-control.metadata.json",
            ROOT / "docs" / "60_interfaces" / "slinky-capacity-observation-control.metadata.json",
            ROOT / "docs" / "60_interfaces" / "llmtier-management-control.metadata.json",
            ROOT / "docs" / "60_interfaces" / "contracts" / "llmtier-v0.3-contract-specification.metadata.json",
            ROOT / "docs" / "70_verification" / "plans" / "llmtier-v0.3-vv-plan.metadata.json",
            ROOT / "docs" / "70_verification" / "specifications" / "llmtier-v0.3-contract-test-specification.metadata.json",
            ROOT / "docs" / "80_operations" / "llmtier-v0.3-release-and-operations.metadata.json",
        ]
        self.assertEqual(11, len(substantive))
        document_ids = set()
        canonical_paths = set()
        for path in substantive:
            metadata = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual("accepted", metadata["status"])
            self.assertIsNotNone(metadata["reviewed_commit"])
            self.assertNotIn(metadata["document_id"], document_ids)
            self.assertNotIn(metadata["source_path"], canonical_paths)
            document_ids.add(metadata["document_id"])
            canonical_paths.add(metadata["source_path"])

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for source_path in canonical_paths:
            self.assertIn(source_path, readme)
        self.assertIn("overall.runtime_activation=false", readme)

        for decision_name in (
            "llmtier-std-draft16-migration-review.review-decision.json",
            "llmtier-std-c1-interface-contract-review.review-decision.json",
            "llmtier-std-c2-assurance-review.review-decision.json",
            "llmtier-std-c3-requirements-review.review-decision.json",
            "llmtier-std-c4-operations-review.review-decision.json",
        ):
            terminal = json.loads((ROOT / "docs" / "91_reviews" / decision_name).read_text(encoding="utf-8"))
            self.assertEqual("ACCEPTED", terminal["verdict"])
            self.assertTrue(terminal["reviewers"])
            self.assertIsNotNone(terminal["decided_at"])
            self.assertIsNotNone(terminal["decision_commit"])
            self.assertFalse(terminal["runtime_activation_requested"])

        for legacy in (
            ROOT / "docs" / "99_reference" / "design" / "llmtier-v0.3-design-review.md",
            ROOT / "docs" / "99_reference" / "contracts" / "piko-data-plane-contract-v0.3.md",
            ROOT / "docs" / "99_reference" / "contracts" / "slinky-capacity-observation-contract-v0.3.md",
            ROOT / "docs" / "99_reference" / "contracts" / "llmtier-management-contract-v0.3.md",
            ROOT / "docs" / "99_reference" / "verification" / "llm-tier-contract-qa-v0.3.md",
        ):
            self.assertIn("Document Status: Superseded", legacy.read_text(encoding="utf-8"))

    def test_slinky_boundary_clarification_separates_upstream_choice_from_api_execution(self):
        path = ROOT / "docs" / "60_interfaces" / "slinky-capacity-observation-control.md"
        text = path.read_text(encoding="utf-8")
        metadata = json.loads(path.with_suffix(".metadata.json").read_text(encoding="utf-8"))
        self.assertEqual("0.3.0", metadata["document_version"])
        self.assertIn("| Document Version | 0.3.0 |", text)
        self.assertIn("适用于 LLMTier API 对单次请求的 Service Level 解析与执行", text)
        self.assertIn("Slinky 上游逻辑路由层的 same-tier fallback/Upshift", text)
        self.assertIn("明确 canonical service_level_id 提交并重新接受 admission", text)
        self.assertIn("不得借此取得 physical routing authority", text)
        self.assertIn("上游决策不属于 Observation API 的执行能力", text)

        evidence = (ROOT / "docs" / "98_migration" / "evidence" / "c5-consumer-verdicts.txt").read_text(encoding="utf-8")
        self.assertIn("P-20260907-e009921eda0a", evidence)
        self.assertIn("S-20260907-8866534be612", evidence)
        self.assertIn("SLK-BOUNDARY-001", evidence)
        self.assertIn("S-20260907-45938693e578", evidence)
        self.assertIn("Verdict: ACCEPTED; SLK-BOUNDARY-001 CLOSED", evidence)

    def test_c6_project_rag_manifest_is_commit_bound_acl_scoped_and_authority_unique(self):
        manifest_path = ROOT / "rag" / "project-ingestion-manifest.jsonl"
        entries = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines() if line]
        self.assertEqual(11, len(entries))

        expected_paths = set()
        for metadata_path in ROOT.joinpath("docs").rglob("*.metadata.json"):
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if metadata["status"] == "accepted" and metadata["document_type"] != "review.packet":
                expected_paths.add(metadata["source_path"])

        actual_paths = {entry["path"] for entry in entries}
        self.assertEqual(expected_paths, actual_paths)
        self.assertEqual(len(entries), len({entry["document_id"] for entry in entries}))
        self.assertEqual(len(entries), len(actual_paths))

        import hashlib

        for entry in entries:
            self.assertEqual("llmtier-project-rag.v1", entry["schema_version"])
            self.assertEqual("corezilla/LLMTier", entry["repository"])
            self.assertEqual("503d0a03fa92aeeb7657ce7ed54bab8b77efef34", entry["commit"])
            self.assertEqual("accepted", entry["document_status"])
            self.assertEqual("project", entry["visibility"])
            self.assertEqual("llmtier", entry["authority"])
            self.assertEqual("project/llmtier", entry["namespace"])
            self.assertTrue(entry["include"])
            published_bytes = subprocess.check_output(
                ["git", "show", f'{entry["commit"]}:{entry["path"]}'],
                cwd=ROOT,
            )
            self.assertEqual(
                hashlib.sha256(published_bytes).hexdigest(),
                entry["content_sha256"],
            )

        excluded = {
            "docs/99_reference/design/llmtier-v0.3-design-review.md",
            "docs/99_reference/contracts/piko-data-plane-contract-v0.3.md",
            "docs/99_reference/contracts/slinky-capacity-observation-contract-v0.3.md",
            "docs/99_reference/contracts/llmtier-management-contract-v0.3.md",
            "docs/99_reference/verification/llm-tier-contract-qa-v0.3.md",
            "rag/std-ingestion-manifest.jsonl",
        }
        self.assertTrue(excluded.isdisjoint(actual_paths))
        self.assertFalse(any(path.startswith("docs/91_reviews/") for path in actual_paths))
        self.assertFalse(any(path.startswith("docs/98_migration/") for path in actual_paths))

        def acl_filter(*, project_scope, authority):
            if project_scope != "LLMTier" or authority != "llmtier":
                return []
            return entries

        self.assertEqual(11, len(acl_filter(project_scope="LLMTier", authority="llmtier")))
        self.assertEqual([], acl_filter(project_scope="Piko", authority="llmtier"))
        self.assertEqual([], acl_filter(project_scope="LLMTier", authority="std"))

        def retrieve(terms):
            allowed = acl_filter(project_scope="LLMTier", authority="llmtier")
            return {
                entry["path"]
                for entry in allowed
                if all(
                    term in subprocess.check_output(
                        ["git", "show", f'{entry["commit"]}:{entry["path"]}'],
                        cwd=ROOT,
                        text=True,
                    )
                    for term in terms
                )
            }

        self.assertIn(
            "docs/60_interfaces/piko-data-plane-control.md",
            retrieve(["model 字段等于 exact", "alias", "Role selector"]),
        )
        self.assertIn(
            "docs/60_interfaces/slinky-capacity-observation-control.md",
            retrieve(["same-tier fallback/Upshift", "重新接受 admission"]),
        )
        runtime_hits = retrieve(["Runtime Activation", "NOT_RUN/BLOCKED"])
        self.assertIn("docs/70_verification/plans/llmtier-v0.3-vv-plan.md", runtime_hits)
        self.assertIn("docs/80_operations/llmtier-v0.3-release-and-operations.md", runtime_hits)

    def test_c7_repository_layout_uses_interfaces_and_reference_trees_without_duplicate_paths(self):
        expected = {
            ROOT / "interfaces" / "openapi" / "llmtier-v0.3.openapi.json",
            ROOT / "interfaces" / "compatibility" / "compatibility-manifest-v0.3.json",
            ROOT / "interfaces" / "schemas" / "llmtier-contracts-v0.2.schema.json",
            ROOT / "interfaces" / "vectors" / "v0.3" / "recovery-protocol-fixtures.json",
            ROOT / "docs" / "99_reference" / "design" / "llmtier-v0.3-design-review.md",
            ROOT / "docs" / "99_reference" / "contracts" / "piko-data-plane-contract-v0.3.md",
            ROOT / "docs" / "99_reference" / "verification" / "llm-tier-contract-qa-v0.3.md",
            ROOT / "docs" / "99_reference" / "future" / "llmtier-v0.4-data-plane.md",
            ROOT / "docs" / "98_migration" / "source-provenance-v0.1.md",
        }
        self.assertTrue(all(path.is_file() for path in expected))

        old_roots = [
            ROOT / "docs" / "contracts",
            ROOT / "docs" / "design",
            ROOT / "docs" / "qa",
            ROOT / "docs" / "future",
            ROOT / "docs" / "migration",
        ]
        self.assertFalse(any(path.is_file() for root in old_roots for path in root.rglob("*") if root.exists()))

        manifest = json.loads(
            (ROOT / "interfaces" / "compatibility" / "compatibility-manifest-v0.3.json").read_text(encoding="utf-8")
        )
        self.assertEqual("openapi/llmtier-v0.3.openapi.json", manifest["contract_authority"]["path"])
        self.assertFalse(manifest["overall"]["runtime_activation"])

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("interfaces/openapi/llmtier-v0.3.openapi.json", readme)
        self.assertIn("docs/98_migration/source-provenance-v0.1.md", readme)


if __name__ == "__main__":
    unittest.main()
