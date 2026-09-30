#!/usr/bin/env bash
# Shared run harness for LLMTier test runners (plan §7).
#
# Sourced by runner_a.sh / runner_b.sh (system) and tests/unit/v03/runner.sh.
# Responsibilities:
#   - resolve a real Run dir (tests/<layer>/reports/<run-id>/)
#   - pin run metadata (run id, git commit, schema_version, openapi version)
#   - run pytest with --junitxml + captured stdout
#   - map pytest exit code -> llmtier run exit code (0/1/2)
#
# Run ID rules:
#   system : <date>/<class>-<phase>   e.g. 2026-09-30/A-api
#   unit   : run-YYYYMMDD-NN           e.g. run-20260930-01
#
# Exit semantics (plan §8 / §9):
#   0 = ok (no FAIL / BLOCKED / INVALID; SKIP within cap)
#   1 = failures/errors (FAIL / BLOCKED / INVALID present)
#   2 = skip/blocked cap breached, or harness/preflight error

# shellcheck shell=bash

_run_timestamp() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
_run_date() { date -u +"%Y-%m-%d"; }

# Locate repo root from this file: tests/lib/ -> repo root is two levels up.
_run_repo_root() {
  cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd
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
  mkdir -p "$root/tests/unit/v03/reports"
  for i in $(seq -w 1 99); do
    candidate="run-${date}-${i}"
    if [ ! -d "$root/tests/unit/v03/reports/$candidate" ]; then
      echo "$candidate"
      return 0
    fi
  done
  echo "run-${date}-99"
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
    echo "python=$("python3" -c 'import platform,sys;print(sys.version.split()[0]+" ("+platform.machine()+")")' 2>/dev/null || echo unknown)"
  } > "$path"
}

# Main entry: run the given pytest arguments under a run dir.
#   _run_pytest <layer-root> <run-id> <layer-label> <exit-semantics:system|unit> -- <pytest args...>
_run_pytest() {
  local layer_root="$1" run_id="$2" layer="$3" semantics="$4"
  shift 4

  local run_dir="$layer_root/reports/$run_id"
  local xml="$run_dir/junit.xml"
  local strip_xml="$run_dir/junit.strip.xml"
  local log="$run_dir/pytest.log"
  mkdir -p "$run_dir/artifacts"

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

  # Produce case-status.json + per-case manifests (plan §7 mandatory mapping).
  python3 "$_RUN_REPO_ROOT/tools/test_report.py" \
    --junit "$xml" \
    --run-metadata "$run_dir/test-run.env" \
    --rootdir "$_RUN_REPO_ROOT" \
    --manifests \
    --out "$run_dir/case-status.json" || true

  # Map pytest exit code -> run exit code.
  # pytest: 0 ok, 1 tests failed, 2 interrupted/collect error, 3 internal, 4 usage, 5 no tests.
  local run_rc
  case "$rc" in
    0) run_rc=0 ;;
    5) run_rc=2 ;;  # no tests collected -> harness error (marker matched nothing)
    *) run_rc=1 ;;
  esac

  # Cap breach -> exit 2 (plan §8: SKIP cap A<=5 / B<=3; runner exit code 2).
  local cap_breached
  cap_breached="$(python3 "$_RUN_REPO_ROOT/tools/test_report.py" \
      --junit "$xml" --run-metadata "$run_dir/test-run.env" \
      --rootdir "$_RUN_REPO_ROOT" \
      --check-cap --layer "$layer" 2>/dev/null || echo "0")"
  if [ "$cap_breached" = "1" ]; then
    run_rc=2
  fi

  echo "$run_rc"
}
