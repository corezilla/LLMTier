"""ST-UI-006 — real browser-driven UI case (RISK-UI-EXEC-1).

Run:  PYTHONPATH=src python3 -m pytest tests/system/cases/ST-UI-006.py -m ui -q
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
    "id": 'ST-UI-006',
    "vrc": 'VRC-UI-006',
    "title": 'diagnostics 4 tabs render/switch and the Disabled state is painted',
    "steps": [{'action': 'click', 'selector': "nav button[data-page='diagnostics']"}, {'action': 'assert', 'expression': "document.querySelectorAll('[data-dtab]').length", 'op': 'equals', 'expected': 4}, {'action': 'assert', 'expression': "document.querySelector('#snapshots.dsub.active').id", 'op': 'equals', 'expected': 'snapshots'}, {'action': 'waitFor', 'expression': "document.querySelector('#snapshots-body').textContent.includes('Disabled')"}, {'action': 'click', 'selector': "[data-dtab='dstats']"}, {'action': 'assert', 'expression': "document.querySelector('#dstats.dsub.active').id", 'op': 'equals', 'expected': 'dstats'}, {'action': 'waitFor', 'expression': "document.querySelector('#dstats-body').textContent.includes('Disabled')"}, {'action': 'assertNetwork', 'urlContains': '/v1/diagnostics', 'method': 'GET', 'status': 200}, {'action': 'assertNoNetwork', 'urlContains': '/v1/diagnostics/stats', 'method': 'GET'}],
}


@pytest.mark.ui
def test_ui_scenario(ui_instance, ui_node, ui_browser, record_property):
    """ST-UI-006 — diagnostics 4 tabs render/switch and the Disabled state is painted."""
    record_property("case_id", SCENARIO["id"])
    out_dir = artifact_dir() / SCENARIO["id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    result = run_scenario(ui_node, {
        "baseUrl": ui_instance.base_url, "path": "/ui/", "steps": SCENARIO["steps"],
    }, out_dir, SCENARIO["id"])
    assert result["ok"], f'{SCENARIO["id"]} failed: {result["failures"]}\nnetwork={result["_networkLog"]}'
    assert_ui_evidence(result)
