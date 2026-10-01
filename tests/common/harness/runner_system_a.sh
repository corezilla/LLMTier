#!/usr/bin/env bash
# A 类 runner：只跑标记为 api_a 的 m5air 现有 state case（读 / 无状态写）
#
# 退出码（plan §7/§8）：
#   0 = 无 FAIL/BLOCKED/INVALID 且 SKIP 未超上限（A ≤5）
#   1 = 有 FAIL/BLOCKED/INVALID（TEST_REPORT_RC=1 透传）
#   2 = SKIP 超上限 / 采集或 harness 错误
#
# 产物（plan §7 / STD repository-layout.md §4.1.1，平铺）：tests/system/reports/<date>/A-api/{<Case ID>.json,
# case-status.json,test-run.env,artifacts/{junit.xml,pytest.log}}
set -euo pipefail

_RUN_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
# shellcheck source=tests/common/harness/run_harness.sh
source "$_RUN_REPO_ROOT/tests/common/harness/run_harness.sh"

cd "$_RUN_REPO_ROOT"
export PYTHONPATH=src

RUN_ID="$(_run_system_run_id "$_RUN_REPO_ROOT/tests/system" "A")"
RUN_DIR="tests/system/reports/$RUN_ID"

rc="$(_run_pytest tests/system "$RUN_ID" "A" "system" \
  tests/system/cases/ -m api_a -v \
  --tb=short \
  -o "addopts=" \
  "$@")"

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
