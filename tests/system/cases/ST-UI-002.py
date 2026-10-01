"""ST-UI-002 — real browser-driven UI case (RISK-UI-EXEC-1).

Run:  PYTHONPATH=src python3 -m pytest tests/system/cases/ST-UI-002.py -m ui -q
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
    "id": 'ST-UI-002',
    "vrc": 'VRC-UI-001',
    "title": 'tab switch toggles the active section and triggers its API call',
    "steps": [{'action': 'assert', 'expression': "document.querySelector('.page.active').id", 'op': 'equals', 'expected': 'home'}, {'action': 'assertNoNetwork', 'urlContains': '/v1/stats', 'method': 'GET'}, {'action': 'click', 'selector': "nav button[data-page='stats']"}, {'action': 'assertVisibleSection', 'expected': 'stats'}, {'action': 'waitFor', 'expression': "document.querySelector('#stats-body').children.length > 0"}, {'action': 'assertNetwork', 'urlContains': '/v1/stats', 'method': 'GET', 'status': 200}, {'action': 'click', 'selector': "nav button[data-page='diagnostics']"}, {'action': 'assertVisibleSection', 'expected': 'diagnostics'}, {'action': 'waitFor', 'expression': "document.querySelectorAll('[data-dtab]').length === 4"}, {'action': 'click', 'selector': "[data-dtab='traces']"}, {'action': 'assert', 'expression': "document.querySelector('#traces.dsub.active').id", 'op': 'equals', 'expected': 'traces'}, {'action': 'assertNetwork', 'urlContains': '/v1/diagnostics/traces', 'method': 'GET', 'status': 200}],
}


@pytest.mark.ui
def test_ui_scenario(ui_instance, ui_node, ui_browser, record_property):
    """ST-UI-002 — tab switch toggles the active section and triggers its API call."""
    record_property("case_id", SCENARIO["id"])
    out_dir = artifact_dir() / SCENARIO["id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    result = run_scenario(ui_node, {
        "baseUrl": ui_instance.base_url, "path": "/ui/", "steps": SCENARIO["steps"],
    }, out_dir, SCENARIO["id"])
    assert result["ok"], f'{SCENARIO["id"]} failed: {result["failures"]}\nnetwork={result["_networkLog"]}'
    assert_ui_evidence(result)
