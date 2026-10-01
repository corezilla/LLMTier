"""ST-UI-005 — real browser-driven UI case (RISK-UI-EXEC-1).

Run:  PYTHONPATH=src python3 -m pytest tests/system/cases/ST-UI-005.py -m ui -q
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
    "id": 'ST-UI-005',
    "vrc": 'VRC-UI-005',
    "title": 'unconfirmed probe does not touch the network; confirmed probe POSTs',
    "steps": [{'action': 'eval', 'expression': 'window.__confirmCount=0;window.confirm=()=>{window.__confirmCount++;return false}'}, {'action': 'waitFor', 'expression': "document.querySelectorAll('#tree .backend-probe').length > 0"}, {'action': 'click', 'selector': '#tree .backend-probe'}, {'action': 'assert', 'expression': 'window.__confirmCount', 'op': 'gte', 'expected': 1}, {'action': 'assertNoNetwork', 'urlContains': '/v1/probes', 'method': 'POST'}, {'action': 'eval', 'expression': 'window.confirm=()=>true'}, {'action': 'click', 'selector': '#tree .backend-probe'}, {'action': 'waitForNetwork', 'urlContains': '/v1/probes', 'method': 'POST', 'status': 200}, {'action': 'assertNetwork', 'urlContains': '/v1/probes', 'method': 'POST', 'status': 200}, {'action': 'assertNetworkCount', 'urlContains': '/v1/probes', 'method': 'POST', 'count': 1}],
}


@pytest.mark.ui
def test_ui_scenario(ui_instance, ui_node, ui_browser, record_property):
    """ST-UI-005 — unconfirmed probe does not touch the network; confirmed probe POSTs."""
    record_property("case_id", SCENARIO["id"])
    out_dir = artifact_dir() / SCENARIO["id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    result = run_scenario(ui_node, {
        "baseUrl": ui_instance.base_url, "path": "/ui/", "steps": SCENARIO["steps"],
    }, out_dir, SCENARIO["id"])
    assert result["ok"], f'{SCENARIO["id"]} failed: {result["failures"]}\nnetwork={result["_networkLog"]}'
    assert_ui_evidence(result)
