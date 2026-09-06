import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "docs" / "std.lock.json"


class StdMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        cls.manifest_path = ROOT / cls.lock["manifest_path"]
        cls.sources = [json.loads(line) for line in cls.manifest_path.read_text(encoding="utf-8").splitlines() if line]

    def test_draft_lock_resolves_to_source_manifest_without_claiming_revision(self):
        self.assertEqual("0.1.0-draft.1", self.lock["std_version"])
        self.assertIsNone(self.lock["source_revision"])
        self.assertTrue(self.manifest_path.is_file())

    def test_source_manifest_records_only_std_sources_with_sha256(self):
        self.assertEqual(8, len(self.sources))
        self.assertEqual(len(self.sources), len({item["source_path"] for item in self.sources}))
        for item in self.sources:
            self.assertEqual("LLMTier", item["project"])
            self.assertEqual("std", item["authority"])
            self.assertEqual("corezilla/architecture-standards", item["source_repository"])
            self.assertIsNone(item["source_commit"])
            self.assertEqual("draft", item["status"])
            self.assertRegex(item["content_sha256"], r"^[a-f0-9]{64}$")

    def test_metadata_template_hashes_are_present_in_source_manifest(self):
        source_hashes = {item["source_path"]: item["content_sha256"] for item in self.sources}
        expected = {
            ROOT / "docs" / "design" / "llmtier-v0.3-system-design.metadata.json": "templates/design/system-design.md",
            ROOT / "docs" / "management" / "std-tailoring-v0.1.metadata.json": "templates/management/tailoring-manifest.md",
        }
        for metadata_path, source_path in expected.items():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertEqual("review", metadata["status"])
            self.assertEqual(source_hashes[source_path], metadata["template_sha256"])


if __name__ == "__main__":
    unittest.main()
