"""ST-UI-003 — real browser-driven UI case (RISK-UI-EXEC-1).

Run:  PYTHONPATH=src python3 -m pytest tests/system/cases/ST-UI-003.py -m ui -q
      (or tools/run_ui_tests.sh)

Drives the live src/web_ui application in headless Chrome via CDP
(tests/common/drivers/browser_driver.mjs) against a hermetic temporary LLMTier
instance (loopback) + the LAN fake provider.  Fixtures live in
tests/system/conftest.py; the runner in tests/common/drivers/ui_support.py.
"""
from __future__ import annotations

import pytest

from tests.system.conftest import artifact_dir, assert_ui_evidence, baseline_settings, run_scenario
from tests.system.conftest import LLMTierInstance  # noqa: F401

pytestmark = pytest.mark.ui


SCENARIO = {
    "id": 'ST-UI-003',
    "vrc": 'VRC-UI-003',
    "title": 'confirm-gated Pause issues If-Match PATCH and the row re-renders',
    "steps": [{'action': 'eval', 'expression': 'window.confirm=()=>true'}, {'action': 'waitFor', 'expression': "document.querySelectorAll('#tree .backend-toggle').length > 0"}, {'action': 'assert', 'expression': "document.querySelector('#tree .backend .status-icon').getAttribute('aria-label')", 'op': 'equals', 'expected': 'Idle'}, {'action': 'assert', 'expression': "fetch('/v1/deployments').then(r=>r.json()).then(j=>j.data.find(d=>d.id==='depl_b').enabled)", 'op': 'equals', 'expected': True}, {'action': 'screenshot', 'name': 'before'}, {'action': 'click', 'selector': '#tree .backend-toggle'}, {'action': 'waitForNetwork', 'urlContains': '/v1/deployments/', 'method': 'PATCH', 'status': 200}, {'action': 'waitFor', 'expression': "document.querySelector('#tree .backend .status-icon').getAttribute('aria-label') === 'Paused'"}, {'action': 'assertNetwork', 'urlContains': '/v1/deployments/', 'method': 'PATCH', 'status': 200}, {'action': 'assertRequestHeader', 'urlContains': '/v1/deployments/', 'method': 'PATCH', 'header': 'If-Match', 'matches': '^"depl_b\\.v[0-9]+"$'}, {'action': 'assert', 'expression': "fetch('/v1/deployments').then(r=>r.json()).then(j=>j.data.find(d=>d.id==='depl_b').enabled)", 'op': 'equals', 'expected': False}, {'action': 'assertNetwork', 'urlContains': '/v1/deployments', 'method': 'GET'}, {'action': 'assert', 'expression': "document.querySelector('#tree .backend .status-icon').getAttribute('aria-label')", 'op': 'equals', 'expected': 'Paused'}, {'action': 'assert', 'expression': "!document.querySelector('#tree .backend .status-icon').getAttribute('aria-label').includes('Idle')", 'op': 'truthy'}, {'action': 'screenshot', 'name': 'after'}, {'action': 'eval', 'expression': 'window.confirm=()=>true'}, {'action': 'click', 'selector': '#tree .backend-toggle'}, {'action': 'waitFor', 'expression': "document.querySelector('#tree .backend .status-icon').getAttribute('aria-label') === 'Idle'"}, {'action': 'assert', 'expression': "fetch('/v1/deployments').then(r=>r.json()).then(j=>j.data.find(d=>d.id==='depl_b').enabled)", 'op': 'equals', 'expected': True}],
}


@pytest.mark.ui
def test_ui_scenario(ui_instance, ui_node, ui_browser, record_property):
    """ST-UI-003 — confirm-gated Pause issues If-Match PATCH and the row re-renders."""
    record_property("case_id", SCENARIO["id"])
    out_dir = artifact_dir() / SCENARIO["id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    result = run_scenario(ui_node, {
        "baseUrl": ui_instance.base_url, "path": "/ui/", "steps": SCENARIO["steps"],
    }, out_dir, SCENARIO["id"])
    assert result["ok"], f'{SCENARIO["id"]} failed: {result["failures"]}\nnetwork={result["_networkLog"]}'
    assert_ui_evidence(result)
