import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V03 = ROOT / "interfaces" / "vectors" / "v0.3"


class CurrentFixtureInventoryTests(unittest.TestCase):
    def test_current_fixture_inventory_is_simplified(self):
        self.assertEqual(
            {
                "admin-model-fixtures.json",
                "openai-surface-fixtures.json",
                "stateless-gateway-boundary-fixtures.json",
                "usage-fixtures.json",
            },
            {path.name for path in V03.glob("*.json")},
        )

    def test_all_current_fixtures_parse_and_share_version(self):
        for path in V03.glob("*.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual("0.3-simplified-candidate.2", payload["fixture_version"], path)
            self.assertTrue(payload["cases"], path)

    def test_removed_contract_fixtures_are_absent(self):
        for name in [
            "recovery-protocol-fixtures.json", "embedding-recovery-fixtures.json",
            "deadline-seat-fairness-fixtures.json", "observation-cost-fixtures.json",
            "capacity-semantic-negative-fixtures.json", "authorization-scope-fixtures.json",
        ]:
            self.assertFalse((V03 / name).exists(), name)


if __name__ == "__main__":
    unittest.main()
