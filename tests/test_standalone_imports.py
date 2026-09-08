from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class StandaloneImportTests(unittest.TestCase):
    def test_flat_source_layout(self) -> None:
        self.assertFalse((ROOT / "src" / "llm_tier").exists())
        self.assertFalse((ROOT / "web").exists())
        self.assertTrue((ROOT / "src" / "web" / "tier.html").is_file())

    def test_public_package_and_entrypoints_import(self) -> None:
        import tier
        from client import TierClient
        from server import TierServer

        self.assertIsNotNone(tier)
        self.assertIsNotNone(TierClient)
        self.assertIsNotNone(TierServer)

    def test_extracted_utility_dependencies_import(self) -> None:
        from stats.llm_stats import build_llm_stats_payload
        from utils.response_parser import ResponseParser
        from utils.sqlite import load_sqlite_module

        self.assertIsNotNone(build_llm_stats_payload)
        self.assertIsNotNone(ResponseParser)
        self.assertTrue(hasattr(load_sqlite_module(), "connect"))


if __name__ == "__main__":
    unittest.main()
