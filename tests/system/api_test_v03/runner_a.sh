#!/usr/bin/env bash
# A 类 runner：只跑标记为 api_a 的 m5air 现有 state case（读 / 无状态写）
#
# 退出码（plan §7/§8）：
#   0 = 无 FAIL/BLOCKED/INVALID 且 SKIP 未超上限（A ≤5）
#   1 = 有 FAIL/BLOCKED/INVALID（TEST_REPORT_RC=1 透传）
#   2 = SKIP 超上限 / 采集或 harness 错误
#
# 产物（plan §7）：tests/system/reports/<date>/A-api/{junit.xml,test-run.env,
# case-status.json,cases/<case-id>/manifest.json,pytest.log,artifacts/}
set -euo pipefail

_RUN_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
# shellcheck source=tests/lib/run_harness.sh
source "$_RUN_REPO_ROOT/tests/lib/run_harness.sh"

cd "$_RUN_REPO_ROOT"
export PYTHONPATH=src

RUN_ID="$(date -u +%Y-%m-%d)/A-api"
RUN_DIR="tests/system/reports/$RUN_ID"

rc="$(_run_pytest tests/system "$RUN_ID" "A" "system" \
  tests/system/api_test_v03/ -m api_a -v \
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
