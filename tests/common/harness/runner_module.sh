#!/usr/bin/env bash
# Module runner (module test plan §7, module test plan §5.1).
#
# Usage:
#   bash tests/common/harness/runner_module.sh                # full suite
#   bash tests/common/harness/runner_module.sh -k MT-UTIL     # slice by -k
#   bash tests/common/harness/runner_module.sh tests/module/cases/MT-UTIL-001.py
#
# Run ID: run-YYYYMMDD-NN (module test plan §7).
# Product (STD repository-layout.md §4.1.1, flat):
#   tests/module/reports/<run-id>/{<Case ID>.json,case-status.json,test-run.env,
#       module-test-report.md,module-test-report.metadata.json,artifacts/{junit.xml,pytest.log}}
#
# 退出码：
#   0 = 全部 PASS（或非阻断状态），1 = 有 FAIL/BLOCKED/INVALID，2 = harness/采集错误
set -euo pipefail

_RUN_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
# shellcheck source=tests/common/harness/run_harness.sh
source "$_RUN_REPO_ROOT/tests/common/harness/run_harness.sh"

cd "$_RUN_REPO_ROOT"
export PYTHONPATH=src

# Module run ids share the unit numbering scheme (run-YYYYMMDD-NN) but are
# allocated in the module report root, so a module run never clobbers a unit run.
_run_module_run_id() {
  local root="$1" date today i candidate
  today="$(_run_date)"
  date="${today//-/}"
  mkdir -p "$root/tests/module/reports"
  for i in $(seq -w 1 99); do
    candidate="run-${date}-${i}"
    if [ ! -d "$root/tests/module/reports/$candidate" ]; then
      echo "$candidate"
      return 0
    fi
  done
  echo "run-${date}-99"
}

RUN_ID="$(_run_module_run_id "$_RUN_REPO_ROOT")"
RUN_DIR="tests/module/reports/$RUN_ID"

# Default target is the whole module suite; extra args (paths / -k) override.
if [ "$#" -eq 0 ]; then
  set -- tests/module/cases
fi

rc="$(_run_pytest tests/module "$RUN_ID" "MODULE" "module" "$@")"

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
