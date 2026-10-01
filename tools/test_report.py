#!/usr/bin/env python3
"""Per-case status mapping for LLMTier run evidence (plan §7).

Reads a pytest JUnit XML plus the run metadata written by the runners and
emits a deterministic ``case-status.json`` mapping.

Status rules (system test plan §7 / unit test plan §7):

    failed      -> FAIL
    errored     -> BLOCKED   (environmental)  *or* FAIL (assertion), see below
    xfailed     -> BLOCKED   reason = the ``BLOCKED (...)`` message
    xpassed     -> XPASS (warn; never counted as PASS)
    skipped     -> SKIP  (environmental skip) | NOT_RUN (planned skip)
    passed      -> PASS (unless newly-required case never ran -> NOT_RUN)

The mapping is deliberately conservative: an ``xfailed`` (and, by default, an
errored) test is a release blocker (BLOCKED), never a silent PASS.

Case IDs come from the ``Case ID:`` header in the test module docstring; when
absent, they are derived from the test path/function name (deterministic).

Also implements the per-case ``manifest.json`` emission (plan §7): each case
gets ``<run-dir>/cases/<case-id>/manifest.json`` recording only facts actually
available (run id, node id, status, reason, timestamps, optional artifacts).

Usage::

    tools/test_report.py --junit <run-dir>/junit.xml \
        --run-metadata <run-dir>/test-run.env --out <run-dir>/case-status.json
    tools/test_report.py --junit <xml> --check-cap --layer <label>

``--check-cap`` prints the verdict ``1`` when the SKIP cap is breached (exit 1)
and ``0`` when within the cap (exit 0). A missing/unreadable junit XML is a
harness error: it prints ``1`` and exits 2 (never a false-safe 0). The runners
consume the printed verdict (see ``tests/common/harness/run_harness.sh``).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_BLOCKED = "BLOCKED"
STATUS_SKIP = "SKIP"
STATUS_XPASS = "XPASS"
STATUS_NOT_RUN = "NOT_RUN"
STATUS_INVALID = "INVALID"

# Plan §7: SKIP cap per class. A (api_a) <= 5, B (api_b) <= 3.
SKIP_CAPS = {"A": 5, "B": 3}

_CASE_ID_HEADER = re.compile(r"^\s*[\"']{0,3}\s*Case ID:\s*(\S+?)[\s\"']*$", re.MULTILINE)
_CASE_ID_IN_NAME = re.compile(
    r"(?:^|/)(?:at|st)_([a-z0-9_]+?)_(\d+[a-z]?)(?:$|[/.])", re.IGNORECASE
)
# STD 78876c9: the executable file name is the Case ID (UT-*/ST-*).
_CASE_ID_IN_FILENAME = re.compile(r"(?:^|[./])((?:UT|ST)-[A-Z0-9]+-\d+[a-z]?)(?:$|::|\.)")
# System-test executable files keep their historical ``at_<legacy>_<n>.py`` names,
# but Case IDs now follow ``ST-<object>-<NNN>`` (STD 78876c9,
# docs/software-object-identifiers.md §2). This map lets the path fallback
# recover the current Case ID from a legacy filename; the authoritative source
# is still the module-level ``Case ID:`` header (see
# docs/98_migration/llmtier-case-id-migration.md).
_LEGACY_FAMILY_TO_TOKEN = {
    "health": "health", "dp_models": "model", "dp_resp": "resp",
    "dp_emb": "emb", "dp_usage": "usage",
    "adm_prov_models": "pmod", "adm_prov_usage": "pusage",
    "adm_prov": "prov", "adm_depl": "depl", "adm_sl": "sl",
    "adm_probe": "probe", "adm_runtime": "runtime", "adm_stats": "stats",
    "adm_audit": "audit", "adm_logs": "logs", "adm_admin_usage": "ausage",
    "obs_diag": "obsdiag", "obs_snap": "obssnap", "obs_stats": "obsstats",
    "obs_trace": "obstrace", "obs_depl": "obsdepl",
    "obs_reqtrace": "obsreqtrace", "obs_alias": "obsalias",
    "auth": "auth", "uit_ui": "ui",
}
_BLOCKED_MSG = re.compile(r"BLOCKED\s*\(([^)]*)\)\s*:?\s*(.*)", re.DOTALL)


def _text(element) -> str:
    if element is None:
        return ""
    return "".join(element.itertext()).strip()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_metadata(path: Path | None) -> dict:
    meta: dict = {}
    if path is None or not path.exists():
        return meta
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        meta[key.strip()] = value.strip()
    return meta


def case_id_from_source(source: str | None, fallback_name: str) -> str:
    """Extract a Case ID from a test source, else derive one from the name."""
    if source:
        match = _CASE_ID_HEADER.search(source)
        if match:
            return match.group(1)
    # STD 78876c9: executable case scripts are named by Case ID
    # (tests/unit/cases/UT-<OBJ>-<NNN>.py, tests/system/cases/ST-<OBJ>-<NNN>.py),
    # so the file name IS the Case ID — the trivial, authoritative fallback.
    match = _CASE_ID_IN_FILENAME.search(fallback_name)
    if match:
        return match.group(1).upper()
    match = _CASE_ID_IN_NAME.search(fallback_name)
    if match:
        family = match.group(1).lower()
        number = int(re.match(r"\d+", match.group(2)).group(0))
        token = _LEGACY_FAMILY_TO_TOKEN.get(family)
        if token is not None:
            return f"ST-{token.upper()}-{number:03d}"
        return match.group(1).upper().replace("_", "-") + "-" + match.group(2)
    # No path/file signal: derive from the full node id so distinct test
    # functions do not collide into one case.
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", fallback_name.replace("::", "-")).strip("-")
    return cleaned.upper() or "UNKNOWN"


def _classify_failure(testcase) -> tuple[str, str]:
    """Map a single <testcase> element to (status, reason)."""
    failure = testcase.find("failure")
    error = testcase.find("error")
    skipped = testcase.find("skipped")

    if skipped is not None:
        reason = skipped.get("message") or _text(skipped) or "skipped"
        # Distinguish an environmental skip from a planned skip.
        marker = skipped.get("type", "")
        low = reason.lower()
        if marker in {"xfail", "pytest.xfail"} or "blocked" in low:
            status = STATUS_BLOCKED
        elif any(tok in low for tok in ("planned", "not implemented", "not_implemented")):
            status = STATUS_NOT_RUN
        else:
            status = STATUS_SKIP
        return status, reason

    if error is not None:
        # Plan §7 (unit): collection/fixture errors are environmental BLOCKED
        # unless clearly assertion-like. We default to BLOCKED (conservative:
        # never silently PASS / under-report an environment blocker).
        reason = error.get("message") or _text(error)
        return STATUS_BLOCKED, f"error: {reason}"

    if failure is not None:
        message = failure.get("message") or ""
        # pytest encodes xfail outcomes as failure type="pytest.xfail".
        if failure.get("type") == "pytest.xfail" or message.strip().startswith("[XPASS]"):
            if message.strip().startswith("[XPASS]"):
                return STATUS_XPASS, message.strip()
            return STATUS_BLOCKED, message
        # xpass can also surface as a failure in some JUnit producers.
        if "XPASS" in message:
            return STATUS_XPASS, message
        return STATUS_FAIL, message or _text(failure)

    if testcase.find("rerun") is not None:
        # A rerun-success still counts as PASS on the final attempt.
        pass
    return STATUS_PASS, ""


def _xfail_reason(message: str) -> str:
    """Extract the ``BLOCKED (...): ...`` reason from an xfail message."""
    match = _BLOCKED_MSG.search(message or "")
    if match:
        scope = match.group(1).strip()
        detail = match.group(2).strip()
        return f"BLOCKED ({scope}): {detail}" if detail else f"BLOCKED ({scope})"
    return (message or "xfailed").strip()


def _case_id_property(testcase) -> str | None:
    """Return the first ``record_property("case_id", ...)`` value, if any.

    A test module may host several Cases (e.g. a parametrized real-browser UI
    suite) that a single module-level ``Case ID:`` header cannot express. Such a
    test tags each parametrization with ``record_property("case_id", "UIT-...")``
    and that property wins over the source-header/name heuristics.
    """
    for prop in testcase.iter("property"):
        if prop.get("name") == "case_id":
            value = (prop.get("value") or "").strip()
            return value or None
    return None


def _case_source(classname: str, file_attr: str | None, rootdir: Path) -> str | None:
    """Best-effort read of a test module's source for its ``Case ID:`` header.

    pytest's JUnit XML carries no ``file`` attribute by default; the
    ``classname`` is the module's dotted path when invoked from the repo root.
    Try the explicit file attr, then classname-as-path, then classname-as-module.
    """
    candidates: list[Path] = []
    if file_attr:
        candidates.append(Path(file_attr))
    if classname:
        dotted = classname.replace(".", "/")
        candidates.append(rootdir / f"{dotted}.py")
        candidates.append(rootdir / f"{dotted}/__init__.py")
    for candidate in candidates:
        try:
            if candidate.is_file():
                return candidate.read_text(encoding="utf-8")
        except OSError:
            continue
    return None


def harvest(junit_path: Path, rootdir: Path | None = None) -> list[dict]:
    """Parse a JUnit XML and return one record per testcase."""
    rootdir = rootdir or Path.cwd()
    tree = ET.parse(junit_path)
    root = tree.getroot()
    records: list[dict] = []
    for testcase in root.iter("testcase"):
        name = testcase.get("name", "")
        classname = testcase.get("classname", "")
        node_id = f"{classname}::{name}" if classname else name
        source = _case_source(classname, testcase.get("file"), rootdir)
        case_id = _case_id_property(testcase) or case_id_from_source(source, node_id)
        status, reason = _classify_failure(testcase)
        if status == STATUS_BLOCKED and "BLOCKED" in reason:
            reason = _xfail_reason(reason)
        records.append(
            {
                "case_id": case_id,
                "status": status,
                "reason": reason,
                "node_id": node_id,
                "time": float(testcase.get("time") or 0.0),
            }
        )
    return records


def _counts(records: list[dict]) -> dict:
    counts = {s: 0 for s in (STATUS_PASS, STATUS_FAIL, STATUS_BLOCKED, STATUS_SKIP,
                             STATUS_XPASS, STATUS_NOT_RUN, STATUS_INVALID)}
    for record in records:
        counts[record["status"]] = counts.get(record["status"], 0) + 1
    return counts


def cap_breached(records: list[dict], layer: str) -> bool:
    """Return True when the SKIP cap for ``layer`` (A/B) is exceeded."""
    key = layer.strip().upper()
    if key not in SKIP_CAPS:
        return False
    skips = sum(1 for r in records if r["status"] == STATUS_SKIP)
    return skips > SKIP_CAPS[key]


def build_report(junit_path: Path, metadata: dict, rootdir: Path | None = None) -> dict:
    records = harvest(junit_path, rootdir)
    counts = _counts(records)
    blockers = [r for r in records if r["status"] in (STATUS_FAIL, STATUS_BLOCKED,
                                                      STATUS_INVALID)]
    cases = {}
    for record in records:
        cases[record["case_id"]] = {
            "status": record["status"],
            "reason": record["reason"],
            "node_id": record["node_id"],
            "time_seconds": record["time"],
        }
    return {
        "schema_version": 1,
        "run_id": metadata.get("run_id", ""),
        "layer": metadata.get("layer", ""),
        "git_commit": metadata.get("git_commit", ""),
        "schema_version_db": metadata.get("schema_version", ""),
        "openapi_version": metadata.get("openapi_version", ""),
        "generated_at": _now(),
        "counts": counts,
        "release_blocking": len(blockers) > 0,
        "cases": cases,
    }


def emit_manifests(run_dir: Path, records: list[dict], metadata: dict) -> int:
    """Write a per-case manifest.json (plan §7) under <run-dir>/cases/<id>/."""
    written = 0
    for record in records:
        case_dir = run_dir / "cases" / record["case_id"]
        case_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "run_id": metadata.get("run_id", ""),
            "case_id": record["case_id"],
            "node_id": record["node_id"],
            "status": record["status"],
            "reason": record["reason"],
            "git_commit": metadata.get("git_commit", ""),
            "schema_version_db": metadata.get("schema_version", ""),
            "openapi_version": metadata.get("openapi_version", ""),
            "started_at": metadata.get("started_at", ""),
            "command": metadata.get("command", ""),
            "redactions": [],
            "artifacts": [],
        }
        (case_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        written += 1
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--junit", type=Path, help="path to junit XML")
    parser.add_argument("--run-metadata", type=Path, default=None,
                        help="path to test-run.env")
    parser.add_argument("--out", type=Path, default=None,
                        help="write case-status.json here")
    parser.add_argument("--rootdir", type=Path, default=None,
                        help="repo root used to resolve classname -> source file")
    parser.add_argument("--manifests", action="store_true",
                        help="emit per-case manifest.json under <run-dir>/cases/")
    parser.add_argument("--check-cap", action="store_true",
                        help="exit 1 when the SKIP cap for --layer is breached")
    parser.add_argument("--layer", default="", help="layer label (A/B/... )")
    args = parser.parse_args(argv)

    rootdir = args.rootdir or Path(__file__).resolve().parents[1]

    if not args.junit or not args.junit.exists():
        print(f"test_report: no junit at {args.junit}", file=sys.stderr)
        if args.check_cap:
            # A missing junit means the run could not be evaluated — that is a
            # harness error (plan §8: exit 2), never a false "cap not breached".
            print("1")
            return 2
        return 1

    metadata = _read_metadata(args.run_metadata)
    if args.layer and not metadata.get("layer"):
        metadata["layer"] = args.layer

    # A junit that exists but cannot be parsed (truncated/not XML) is equally a
    # harness/collection error (plan §8): never a false-safe exit 0 and never an
    # uncaught traceback. --check-cap prints "1" (harness error) and exits 2.
    try:
        records = harvest(args.junit, rootdir)
    except (ET.ParseError, OSError, ValueError) as exc:
        print(f"test_report: unreadable junit at {args.junit}: {exc}", file=sys.stderr)
        if args.check_cap:
            print("1")
            return 2
        return 2

    if args.check_cap:
        breached = cap_breached(records, args.layer)
        print("1" if breached else "0")
        return 1 if breached else 0

    report = build_report(args.junit, metadata, rootdir)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    else:
        print(json.dumps(report, indent=2, sort_keys=True))

    if args.manifests:
        emit_manifests(args.out.parent if args.out else args.junit.parent,
                       records, metadata)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
