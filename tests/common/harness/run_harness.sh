#!/usr/bin/env bash
# Shared run harness for LLMTier test runners (plan §7).
#
# Sourced by tests/common/harness/runner_system_a.sh / runner_system_b.sh (system)
# and tests/common/harness/runner_unit.sh (unit).
# Responsibilities:
#   - resolve a real Run dir (tests/<layer>/reports/<run-id>/)
#   - pin run metadata (run id, git commit, schema_version, openapi version)
#   - run pytest with --junitxml + captured stdout
#   - map pytest exit code -> llmtier run exit code (0/1/2)
#
# Report layout (STD repository-layout.md §4.1.1):
#   reports/<run-id>/<Case ID>.json   flat per-case result (committed)
#   reports/<run-id>/{unit-test-report.md,*.metadata.json}   formal report
#   reports/<run-id>/{case-status.json,test-run.env}   run root (committed)
#   reports/<run-id>/artifacts/{junit.xml,pytest.log}  framework machine
#       output (ignored / CI-retained), never at the run root.
#
# Run ID rules:
#   system : <date>/<class>-api      e.g. 2026-09-30/A-api   (first run today)
#            <date>/<class>-api-N    e.g. 2026-09-30/A-api-2 (rerun; never clobber)
#   unit   : run-YYYYMMDD-NN         e.g. run-20260930-01
#
# Reruns always allocate a fresh run dir (plan §7: 重跑生成新 Run、新报告，
# 不覆盖旧失败).
#
# Exit semantics (plan §8 / §9):
#   0 = ok (no FAIL / BLOCKED / INVALID; SKIP within cap)
#   1 = failures/errors (FAIL / BLOCKED / INVALID present)
#   2 = skip/blocked cap breached, or harness/preflight error

# shellcheck shell=bash

_run_timestamp() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
_run_date() { date -u +"%Y-%m-%d"; }

# Locate repo root from this file: tests/common/harness/ -> repo root is three levels up.
_run_repo_root() {
  cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd
}

# git_commit: refuse branch/tag/HEAD names; demand a real SHA (plan §2/§7).
_run_git_commit() {
  local root="$1"
  ( cd "$root" && git rev-parse HEAD 2>/dev/null ) || echo "unknown"
}

# schema_version from src/util/store.py::EXPECTED_SCHEMA_VERSION
_run_schema_version() {
  local root="$1"
  python3 - "$root" <<'PY' 2>/dev/null || echo "unknown"
import re, sys
from pathlib import Path
p = Path(sys.argv[1]) / "src" / "util" / "store.py"
m = re.search(r"EXPECTED_SCHEMA_VERSION\s*=\s*(\d+)", p.read_text(encoding="utf-8"))
print(m.group(1) if m else "unknown")
PY
}

# openapi version from interfaces/openapi/llmtier.openapi.json::info.version
_run_openapi_version() {
  local root="$1"
  python3 - "$root" <<'PY' 2>/dev/null || echo "unknown"
import json, sys
from pathlib import Path
p = Path(sys.argv[1]) / "interfaces" / "openapi" / "llmtier.openapi.json"
print(json.loads(p.read_text(encoding="utf-8"))["info"]["version"])
PY
}

# Allocate the next unit run id run-YYYYMMDD-NN for today.
_run_unit_run_id() {
  local root="$1" date today i candidate
  today="$(_run_date)"
  date="${today//-/}"
  mkdir -p "$root/tests/unit/reports"
  for i in $(seq -w 1 99); do
    candidate="run-${date}-${i}"
    if [ ! -d "$root/tests/unit/reports/$candidate" ]; then
      echo "$candidate"
      return 0
    fi
  done
  echo "run-${date}-99"
}

# Allocate the next system run id for today (plan §7: a rerun must produce a
# NEW run and must never overwrite an earlier failure).
# The canonical first run is <date>/<class>-api (e.g. 2026-09-30/A-api); reruns
# append a phase ordinal: <date>/<class>-api-2, <date>/<class>-api-3, ...
#   _run_system_run_id <layer-root> <class-label>
_run_system_run_id() {
  local layer_root="$1" class_label="$2" date today i candidate
  today="$(_run_date)"
  mkdir -p "$layer_root/reports"
  candidate="$today/${class_label}-api"
  if [ ! -d "$layer_root/reports/$candidate" ]; then
    echo "$candidate"
    return 0
  fi
  for i in $(seq 2 99); do
    candidate="$today/${class_label}-api-${i}"
    if [ ! -d "$layer_root/reports/$candidate" ]; then
      echo "$candidate"
      return 0
    fi
  done
  echo "$today/${class_label}-api-99"
}

# Write test-run.env metadata (key=value, machine readable).
_run_write_metadata() {
  local path="$1" run_id="$2" layer="$3" cmd="$4" commit schema openapi
  commit="$(_run_git_commit "$_RUN_REPO_ROOT")"
  schema="$(_run_schema_version "$_RUN_REPO_ROOT")"
  openapi="$(_run_openapi_version "$_RUN_REPO_ROOT")"
  {
    echo "run_id=$run_id"
    echo "layer=$layer"
    echo "git_commit=$commit"
    echo "schema_version=$schema"
    echo "openapi_version=$openapi"
    echo "started_at=$(_run_timestamp)"
    echo "command=$cmd"
    echo "pythonpath=${PYTHONPATH:-unset}"
    echo "python=$("python3" -c 'import platform,sys;print(sys.version.split()[0]+" ("+platform.machine()+")")' 2>/dev/null || echo unknown)"
  } > "$path"
}

# Main entry: run the given pytest arguments under a run dir.
#   _run_pytest <layer-root> <run-id> <layer-label> <exit-semantics:system|unit> -- <pytest args...>
_run_pytest() {
  local layer_root="$1" run_id="$2" layer="$3" semantics="$4"
  shift 4

  local run_dir="$layer_root/reports/$run_id"
  local artifacts_dir="$run_dir/artifacts"
  local xml="$artifacts_dir/junit.xml"
  local strip_xml="$artifacts_dir/junit.strip.xml"
  local log="$artifacts_dir/pytest.log"
  mkdir -p "$artifacts_dir"

  local cmd="python3 -m pytest --junitxml=$xml $*"
  _run_write_metadata "$run_dir/test-run.env" "$run_id" "$layer" "$cmd"

  # pytest output goes to the log file only; stdout of this function must
  # carry just the mapped exit code (callers capture it in $(...)).
  python3 -m pytest --junitxml="$xml" "$@" > "$log" 2>&1
  local rc=$?

  # pytest 5+ strips ANSI when not a tty; older pytest (or -p no:cacheprovider
  # edge cases) may leave color codes that break XML parsers. Normalize.
  if [ -f "$xml" ] && grep -q $'\x1b' "$xml" 2>/dev/null; then
    python3 - "$xml" "$strip_xml" <<'PY'
import re, sys
raw = open(sys.argv[1], "rb").read()
open(sys.argv[2], "wb").write(re.sub(rb"\x1b\[[0-9;]*m", b"", raw))
PY
    mv "$strip_xml" "$xml"
  fi

  # Map pytest exit code -> run exit code.
  # pytest: 0 ok, 1 tests failed, 2 interrupted/collect error, 3 internal, 4 usage, 5 no tests.
  local run_rc
  case "$rc" in
    0) run_rc=0 ;;
    5) run_rc=2 ;;  # no tests collected -> harness error (marker matched nothing)
    *) run_rc=1 ;;
  esac

  # Produce case-status.json + flat per-case <Case ID>.json (plan §7 mandatory
  # mapping). test_report.py also prints the SKIP-cap verdict ("1"/"0") as its
  # last stdout line, so cap check needs no second junit parse. On a harness
  # error (missing/unreadable junit) the tool prints "1" and exits 2 -> treat
  # the missing verdict as a breach (exit 2), never a false-safe 0.
  local cap_breached
  cap_breached="$(python3 "$_RUN_REPO_ROOT/tools/test_report.py" \
    --junit "$xml" \
    --run-metadata "$run_dir/test-run.env" \
    --rootdir "$_RUN_REPO_ROOT" \
    --manifests \
    --check-cap --layer "$layer" \
    --out "$run_dir/case-status.json" 2>/dev/null)" || true
  cap_breached="$(printf '%s' "$cap_breached" | tail -n1 | tr -d '[:space:]')"
  [ "$cap_breached" = "0" ] || run_rc=2

  # Persist the mapped run exit code at the run root (plan §7: the Run record
  # carries command, versions, stdout and exit code).
  printf 'exit_code=%s\npytest_exit_code=%s\nfinished_at=%s\n' \
    "$run_rc" "$rc" "$(_run_timestamp)" >> "$run_dir/test-run.env"

  echo "$run_rc"
}
