"""Case ID: UT-TOOL-001

Unit tests for tools/test_report.py — the plan §7 status mapping.

Covers the mandatory rules:
  failed -> FAIL
  xfailed -> BLOCKED (reason carried from the ``BLOCKED (...)`` message)
  xpassed -> XPASS (warn; never PASS)
  skipped -> SKIP (environmental) / NOT_RUN (planned)
  error   -> BLOCKED (environmental)
and the run-level SKIP cap (A<=5 / B<=3) and per-case manifest emission.

Deterministic: builds JUnit XML from inline fixtures, no clock/network deps
beyond the fixed ``run-metadata`` file it writes itself.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.test_report import (  # noqa: E402
    STATUS_BLOCKED,
    STATUS_FAIL,
    STATUS_NOT_RUN,
    STATUS_PASS,
    STATUS_SKIP,
    STATUS_XPASS,
    build_report,
    cap_breached,
    case_id_from_source,
    emit_manifests,
    harvest,
    main,
)

METADATA = {
    "run_id": "2026-09-30/A-api",
    "layer": "A",
    "git_commit": "deadbeef",
    "schema_version": "2",
    "openapi_version": "0.3-simplified-candidate.8",
    "command": "python3 -m pytest",
    "started_at": "2026-09-30T00:00:00Z",
}


def _xml(*cases: str) -> str:
    body = "".join(cases)
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<testsuites><testsuite name="pytest">{body}</testsuite></testsuites>'
    )


def _case(name: str, inner: str = "", file: str = "") -> str:
    file_attr = f' file="{file}"' if file else ""
    return f'<testcase classname="tests.unit.v03.test_x" name="{name}" time="0.1"{file_attr}>{inner}</testcase>'


def _write(tmp: Path, content: str, name: str = "junit.xml") -> Path:
    path = tmp / name
    path.write_text(content, encoding="utf-8")
    return path


class StatusMappingTests(unittest.TestCase):
    def test_passed_maps_to_pass(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            xml = _write(tmp, _xml(_case("test_ok")))
            records = harvest(xml)
            self.assertEqual(1, len(records))
            self.assertEqual(STATUS_PASS, records[0]["status"])

    def test_failed_maps_to_fail(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            xml = _write(tmp, _xml(_case("test_bad", '<failure message="boom">tb</failure>')))
            self.assertEqual(STATUS_FAIL, harvest(xml)[0]["status"])

    def test_xfailed_maps_to_blocked_with_reason(self):
        msg = "BLOCKED (ST-USAGE-004): ssh not available for m5air sqlite3 access"
        inner = f'<failure type="pytest.xfail" message="{msg}">x</failure>'
        with tempfile.TemporaryDirectory() as d:
            xml = _write(Path(d), _xml(_case("test_expired", inner)))
            record = harvest(xml)[0]
            self.assertEqual(STATUS_BLOCKED, record["status"])
            self.assertIn("BLOCKED (ST-USAGE-004)", record["reason"])
            self.assertIn("ssh not available", record["reason"])

    def test_xpassed_maps_to_xpass_not_pass(self):
        inner = '<failure message="[XPASS(strict)] unexpected pass">x</failure>'
        with tempfile.TemporaryDirectory() as d:
            xml = _write(Path(d), _xml(_case("test_strict", inner)))
            record = harvest(xml)[0]
            self.assertEqual(STATUS_XPASS, record["status"])
            self.assertNotEqual(STATUS_PASS, record["status"])

    def test_environmental_skip_maps_to_skip(self):
        with tempfile.TemporaryDirectory() as d:
            xml = _write(Path(d), _xml(_case("test_env", '<skipped message="no LAN IP"/>')))
            self.assertEqual(STATUS_SKIP, harvest(xml)[0]["status"])

    def test_planned_skip_maps_to_not_run(self):
        inner = '<skipped message="planned, not implemented this round"/>'
        with tempfile.TemporaryDirectory() as d:
            xml = _write(Path(d), _xml(_case("test_planned", inner)))
            self.assertEqual(STATUS_NOT_RUN, harvest(xml)[0]["status"])

    def test_error_maps_to_blocked(self):
        inner = '<error message="fixture AppFixture failed">tb</error>'
        with tempfile.TemporaryDirectory() as d:
            xml = _write(Path(d), _xml(_case("test_fixture", inner)))
            self.assertEqual(STATUS_BLOCKED, harvest(xml)[0]["status"])


class CaseIdTests(unittest.TestCase):
    def test_case_id_from_docstring_header(self):
        source = '"""Case ID: ST-USAGE-004\n\nEndpoint..."""'
        self.assertEqual("ST-USAGE-004", case_id_from_source(source, "test_x"))

    def test_case_id_falls_back_to_path(self):
        self.assertEqual(
            "ST-MODEL-001",
            case_id_from_source(None, "tests/system/api_test_v03/at_dp_models_01.py::test_x"),
        )

    def test_record_property_case_id_wins_over_source_header(self):
        # A parametrized module (real-browser UI suite) hosts several Cases that
        # one module-level ``Case ID:`` header cannot express; the per-test
        # ``record_property("case_id", ...)`` property must win.
        xml = (
            '<testsuites><testsuite>'
            '<testcase classname="tests.ui.test_ui_browser" name="test_ui_scenario[ST-UI-002]">'
            '<properties><property name="case_id" value="ST-UI-002" /></properties>'
            '</testcase></testsuite></testsuites>'
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            junit = root / "junit.xml"
            junit.write_text(xml)
            records = harvest(junit, rootdir=REPO)
        self.assertEqual(["ST-UI-002"], [r["case_id"] for r in records])


class ReportTests(unittest.TestCase):
    def test_build_report_counts_and_blocking(self):
        xml_content = _xml(
            _case("test_alpha"),
            _case("test_beta", '<failure message="bad">x</failure>'),
            _case("test_gamma", '<failure type="pytest.xfail" message="BLOCKED (X): nope">x</failure>'),
        )
        with tempfile.TemporaryDirectory() as d:
            xml = _write(Path(d), xml_content)
            report = build_report(xml, METADATA)
            self.assertEqual(1, report["counts"][STATUS_PASS])
            self.assertEqual(1, report["counts"][STATUS_FAIL])
            self.assertEqual(1, report["counts"][STATUS_BLOCKED])
            self.assertTrue(report["release_blocking"])
            self.assertEqual("2026-09-30/A-api", report["run_id"])
            self.assertEqual(3, len(report["cases"]))

    def test_cap_not_breached_below_limit(self):
        cases = [_case(f"test_skip_{i}", '<skipped message="env"/>') for i in range(5)]
        with tempfile.TemporaryDirectory() as d:
            xml = _write(Path(d), _xml(*cases))
            self.assertFalse(cap_breached(harvest(xml), "A"))
            self.assertTrue(cap_breached(harvest(xml), "B"))  # B cap is 3

    def test_cap_breached_above_limit(self):
        cases = [_case(f"test_skip_{i}", '<skipped message="env"/>') for i in range(6)]
        with tempfile.TemporaryDirectory() as d:
            xml = _write(Path(d), _xml(*cases))
            self.assertTrue(cap_breached(harvest(xml), "A"))

    def test_check_cap_missing_junit_is_harness_error(self):
        # A missing junit must not be a false-safe "cap not breached": exit 2
        # (plan §8 harness error), printing 1.
        rc = main(["--junit", "/nonexistent/junit.xml", "--check-cap", "--layer", "A"])
        self.assertEqual(2, rc)

    def test_check_cap_malformed_junit_is_harness_error(self):
        # A junit that exists but is not parseable XML (truncated/corrupt) is a
        # harness error too: --check-cap must print 1 and exit 2, never emit an
        # uncaught traceback or a false-safe 0.
        with tempfile.TemporaryDirectory() as d:
            xml = Path(d) / "junit.xml"
            xml.write_text("<testsuites><testsuite><testcase", encoding="utf-8")
            self.assertEqual(2, main(["--junit", str(xml), "--check-cap", "--layer", "A"]))
            self.assertEqual(2, main(["--junit", str(xml), "--out", str(Path(d) / "x.json")]))

    def test_check_cap_within_limit_exits_zero(self):
        cases = [_case(f"test_skip_{i}", '<skipped message="env"/>') for i in range(2)]
        with tempfile.TemporaryDirectory() as d:
            xml = _write(Path(d), _xml(*cases))
            self.assertEqual(0, main(["--junit", str(xml), "--check-cap", "--layer", "A"]))

    def test_check_cap_breached_exits_one(self):
        # Established contract: --check-cap exits 1 on breach, 0 when within cap
        # (the runner maps the printed "1" to its own exit 2). See run_harness.sh.
        cases = [_case(f"test_skip_{i}", '<skipped message="env"/>') for i in range(6)]
        with tempfile.TemporaryDirectory() as d:
            xml = _write(Path(d), _xml(*cases))
            self.assertEqual(1, main(["--junit", str(xml), "--check-cap", "--layer", "A"]))

    def test_emit_manifests(self):
        # STD repository-layout.md §4.1.1: per-case results are FLAT
        # (<run-dir>/<Case ID>.json), never cases/<id>/manifest.json.
        with tempfile.TemporaryDirectory() as d:
            run_dir = Path(d) / "run"
            run_dir.mkdir()
            xml = _write(run_dir, _xml(_case("test_ok")))
            records = harvest(xml)
            written = emit_manifests(run_dir, records, METADATA)
            self.assertEqual(1, written)
            manifest = json.loads((run_dir / f"{records[0]['case_id']}.json").read_text())
            self.assertEqual(records[0]["case_id"], manifest["case_id"])
            self.assertEqual("deadbeef", manifest["git_commit"])
            self.assertEqual([], manifest["redactions"])
            self.assertFalse((run_dir / "cases").exists())


if __name__ == "__main__":
    unittest.main()
