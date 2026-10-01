"""ST-UI-001 — real browser-driven UI case (RISK-UI-EXEC-1).

Run:  PYTHONPATH=src python3 -m pytest tests/system/cases/ST-UI-001.py -m ui -q
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
    "id": 'ST-UI-001',
    "vrc": 'VRC-UI-001',
    "title": 'page renders live and provider rows come from the API',
    "steps": [{'action': 'assert', 'expression': 'document.title', 'op': 'equals', 'expected': 'LLMTier Console'}, {'action': 'assert', 'expression': "document.querySelectorAll('nav button[data-page]').length", 'op': 'equals', 'expected': 5}, {'action': 'assert', 'expression': "!!document.querySelector('#home.page.active')", 'op': 'truthy'}, {'action': 'assert', 'expression': "!!document.querySelector('#tree details .tiername')", 'op': 'truthy'}, {'action': 'click', 'selector': "nav button[data-page='providers']"}, {'action': 'waitFor', 'expression': "document.querySelectorAll('#provider-tree .provider-row').length > 0"}, {'action': 'assert', 'expression': "document.querySelector('#provider-tree .providername b').textContent", 'op': 'equals', 'expected': 'Baseline Provider B'}, {'action': 'assertNetwork', 'urlContains': '/v1/providers', 'method': 'GET', 'status': 200}],
}


@pytest.mark.ui
def test_ui_scenario(ui_instance, ui_node, ui_browser, record_property):
    """ST-UI-001 — page renders live and provider rows come from the API."""
    record_property("case_id", SCENARIO["id"])
    out_dir = artifact_dir() / SCENARIO["id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    result = run_scenario(ui_node, {
        "baseUrl": ui_instance.base_url, "path": "/ui/", "steps": SCENARIO["steps"],
    }, out_dir, SCENARIO["id"])
    assert result["ok"], f'{SCENARIO["id"]} failed: {result["failures"]}\nnetwork={result["_networkLog"]}'
    assert_ui_evidence(result)
