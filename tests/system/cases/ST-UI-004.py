"""ST-UI-004 — real browser-driven UI case (RISK-UI-EXEC-1).

Run:  PYTHONPATH=src python3 -m pytest tests/system/cases/ST-UI-004.py -m ui -q
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
    "id": 'ST-UI-004',
    "vrc": 'VRC-UI-004',
    "title": 'unknown usage is rendered as unknown/empty, never a fabricated zero',
    "steps": [{'action': 'click', 'selector': "nav button[data-page='providers']"}, {'action': 'waitFor', 'expression': "document.querySelectorAll('#provider-tree .provider-row').length > 0"}, {'action': 'assert', 'expression': "document.querySelector('#provider-tree .provider-row summary .unknown')?.textContent || ''", 'op': 'includes', 'expected': 'Not refreshed'}, {'action': 'assert', 'expression': "!/\\d/.test(document.querySelector('#provider-tree .provider-row summary .unknown')?.textContent || '')", 'op': 'truthy'}, {'action': 'click', 'selector': "nav button[data-page='logs']"}, {'action': 'assertVisibleSection', 'expected': 'logs'}, {'action': 'waitFor', 'expression': "document.querySelector('#usage-body').children.length > 0"}, {'action': 'assert', 'expression': "document.querySelector('#usage-body td[colspan]')?.textContent || ''", 'op': 'includes', 'expected': 'No records'}, {'action': 'assert', 'expression': "!/\\d/.test(document.querySelector('#usage-body td[colspan]')?.textContent || '')", 'op': 'truthy'}, {'action': 'click', 'selector': "nav button[data-page='stats']"}, {'action': 'waitFor', 'expression': "document.querySelector('#stats-body').children.length > 0"}, {'action': 'assert', 'expression': "document.querySelector('#stats-body td[colspan]')?.textContent || ''", 'op': 'includes', 'expected': 'No calls recorded'}, {'action': 'assert', 'expression': "!/\\d/.test(document.querySelector('#stats-body td[colspan]')?.textContent || '')", 'op': 'truthy'}],
}


@pytest.mark.ui
def test_ui_scenario(ui_instance, ui_node, ui_browser, record_property):
    """ST-UI-004 — unknown usage is rendered as unknown/empty, never a fabricated zero."""
    record_property("case_id", SCENARIO["id"])
    out_dir = artifact_dir() / SCENARIO["id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    result = run_scenario(ui_node, {
        "baseUrl": ui_instance.base_url, "path": "/ui/", "steps": SCENARIO["steps"],
    }, out_dir, SCENARIO["id"])
    assert result["ok"], f'{SCENARIO["id"]} failed: {result["failures"]}\nnetwork={result["_networkLog"]}'
    assert_ui_evidence(result)
