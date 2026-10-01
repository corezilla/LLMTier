#!/usr/bin/env bash
# B 类 runner：只跑标记为 api_b 的临时 SQLite 实例 case（CRUD / 注入）
# 文件集合由 pytest marker 生成，不再手工维护列表。
#
# 退出码（plan §7/§8）：
#   0 = 无 FAIL/BLOCKED/INVALID 且 SKIP 未超上限（B ≤3）
#   1 = 有 FAIL/BLOCKED/INVALID
#   2 = SKIP 超上限 / 采集或 harness 错误
#
# 产物（plan §7 / STD repository-layout.md §4.1.1，平铺）：tests/system/reports/<date>/B-api/{<Case ID>.json,
# case-status.json,test-run.env,artifacts/{junit.xml,pytest.log}}
set -euo pipefail

_RUN_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
# shellcheck source=tests/common/harness/run_harness.sh
source "$_RUN_REPO_ROOT/tests/common/harness/run_harness.sh"

cd "$_RUN_REPO_ROOT"
export PYTHONPATH=src

RUN_ID="$(_run_system_run_id "$_RUN_REPO_ROOT/tests/system" "B")"
RUN_DIR="tests/system/reports/$RUN_ID"

rc="$(_run_pytest tests/system "$RUN_ID" "B" "system" \
  tests/system/cases/ -m api_b -v \
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
