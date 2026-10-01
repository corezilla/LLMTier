"""ST-UI-009 — real browser-driven UI case (RISK-UI-EXEC-1).

Run:  PYTHONPATH=src python3 -m pytest tests/system/cases/ST-UI-009.py -m ui -q

Pattern: 幂等 / 防重 (idempotency). A rapid double activation of the
confirm-gated Probe button must produce exactly ONE POST /v1/probes.
"""
from __future__ import annotations

import pytest

from tests.system.conftest import artifact_dir, assert_ui_evidence, run_scenario

pytestmark = pytest.mark.ui


@pytest.mark.ui
def test_ui_double_click_probe_is_not_duplicated(ui_instance, ui_node, ui_browser, record_property):
    """ST-UI-009 — Pattern: 幂等 / 防重 (idempotency)."""
    record_property("case_id", "ST-UI-009")
    out_dir = artifact_dir() / "ST-UI-009"
    out_dir.mkdir(parents=True, exist_ok=True)
    steps = [
        {"action": "eval", "expression": "window.confirm=()=>true"},
        {"action": "waitFor", "expression": "document.querySelectorAll('#tree .backend-probe').length > 0"},
        {"action": "assert", "expression": "document.querySelectorAll('#tree details').length", "op": "equals", "expected": 7},
        {"action": "eval", "expression": "(()=>{const b=document.querySelector('#tree .backend-probe');b.click();b.click();return true})()"},
        {"action": "waitForNetwork", "urlContains": "/v1/probes", "method": "POST", "status": 200},
        {"action": "assertNetwork", "urlContains": "/v1/probes", "method": "POST", "status": 200},
        {"action": "assertNetworkCount", "urlContains": "/v1/probes", "method": "POST", "count": 1},
        {"action": "assert", "expression": "document.querySelectorAll('#tree details').length", "op": "equals", "expected": 7},
    ]
    result = run_scenario(ui_node, {
        "baseUrl": ui_instance.base_url, "path": "/ui/", "steps": steps,
    }, out_dir, "ST-UI-009")
    assert result["ok"], f"ST-UI-009 failed: {result['failures']}\nnetwork={result['_networkLog']}"
    assert_ui_evidence(result)
