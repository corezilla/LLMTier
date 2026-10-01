#!/usr/bin/env bash
# Real-browser UI test runner (RISK-UI-EXEC-1).
#
# Drives the live web UI in headless Chrome via CDP against a hermetic
# temporary LLMTier instance (loopback) + the LAN fake provider. No host
# outside loopback is contacted by the page; nothing is downloaded (the
# browser is resolved from an explicit path / cache).
#
# Dependency (env var):
#   LLMTIER_BROWSER  absolute path to Chrome / Chromium / chrome-headless-shell
#                    Default: /Applications/Google Chrome.app/Contents/MacOS/Google Chrome,
#                    then a cached Chromium and chrome-headless-shell.
#   LLMTIER_NODE     node binary (default: newest ~/.nvm/.../v22*/bin/node or $PATH)
#
# Usage:
#   tools/run_ui_tests.sh                 # all UI cases (-m ui)
#   tools/run_ui_tests.sh -k ST-UI-006   # extra pytest args are forwarded
#   LLMTIER_BROWSER=/path/to/chrome tools/run_ui_tests.sh
#
# Artifacts: tests/system/artifacts/<case>/{<case>.png,<case>.network.json}
# (override the base dir with LLMTIER_UI_ARTIFACT_DIR).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PYTHON="${LLMTIER_TEST_PYTHON:-python3}"
export PYTHONPATH="${REPO_ROOT}/src"

# junit_family=xunit1 keeps ``record_property("case_id", ...)`` in the JUnit XML
# (the evidence-chain Case ID mapping in tools/test_report.py) without pytest's
# xunit2 incompatibility warning.
exec "$PYTHON" -m pytest tests/system/cases -m ui -q -o junit_family=xunit1 "$@"
