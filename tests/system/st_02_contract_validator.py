"""ST-02 contract semantic validator (System test plan §4).

Runs tools/contract_semantic_validator_v03.py and asserts exit 0
with empty stdout. Verifies the OpenAPI / manifest / fixture files
in interfaces/ stay in sync with prose docs.
"""
from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]


class ST02ContractValidator(unittest.TestCase):
    def test_validator_exits_zero(self):
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(REPO / "src")
        proc = subprocess.run(
            [sys.executable,
             str(REPO / "tools" / "contract_semantic_validator_v03.py")],
            capture_output=True, env=env, timeout=60)
        # exit 0 with empty stdout is the PASS contract; anything else
        # (non-zero exit, non-empty stdout) is a FAIL
        if proc.returncode != 0 or proc.stdout.strip():
            self.fail(
                f"validator exit={proc.returncode} "
                f"stdout={proc.stdout[:200]!r} "
                f"stderr={proc.stderr[:200]!r}")


if __name__ == "__main__":
    unittest.main()