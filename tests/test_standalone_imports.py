from __future__ import annotations

import unittest


class StandaloneImportTests(unittest.TestCase):
    def test_public_package_and_entrypoints_import(self) -> None:
        import llm_tier
        from llm_tier.client import TierClient
        from llm_tier.server import TierServer

        self.assertIsNotNone(llm_tier)
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
