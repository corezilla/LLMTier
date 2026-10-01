#!/usr/bin/env bash
# Unit runner (plan §7, unit test plan §5.1).
#
# Usage:
#   bash tests/common/harness/runner_unit.sh                # full suite
#   bash tests/common/harness/runner_unit.sh -k UT-UTIL     # slice by -k
#   bash tests/common/harness/runner_unit.sh tests/unit/cases/UT-UTIL-001.py
#
# Run ID: run-YYYYMMDD-NN (unit test plan §7).
# Product (STD repository-layout.md §4.1.1, flat):
#   tests/unit/reports/<run-id>/{<Case ID>.json,case-status.json,test-run.env,
#       unit-test-report.md,unit-test-report.metadata.json,artifacts/{junit.xml,pytest.log}}
#
# 退出码：
#   0 = 全部 PASS（或非阻断状态），1 = 有 FAIL/BLOCKED/INVALID，2 = harness/采集错误
set -euo pipefail

_RUN_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
# shellcheck source=tests/common/harness/run_harness.sh
source "$_RUN_REPO_ROOT/tests/common/harness/run_harness.sh"

cd "$_RUN_REPO_ROOT"
export PYTHONPATH=src

RUN_ID="$(_run_unit_run_id "$_RUN_REPO_ROOT")"
RUN_DIR="tests/unit/reports/$RUN_ID"

# Default target is the whole unit suite; extra args (paths / -k) override.
if [ "$#" -eq 0 ]; then
  set -- tests/unit/cases
fi

rc="$(_run_pytest tests/unit "$RUN_ID" "UNIT" "unit" "$@")"

echo "run dir : $RUN_DIR" >&2
echo "status  : $(python3 - "$RUN_DIR/case-status.json" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    print(d["counts"])
except Exception as exc:  # noqa: BLE001
    print(f"no status ({exc})")
PY
)" >&2

exit "$rc"
