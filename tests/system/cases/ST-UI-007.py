"""ST-UI-007 — real browser-driven UI case (RISK-UI-EXEC-1).

Run:  PYTHONPATH=src python3 -m pytest tests/system/cases/ST-UI-007.py -m ui -q

Injected API 500 → the UI shows the stale banner and keeps the DOM.
Fixtures live in tests/system/conftest.py; the runner in
tests/common/drivers/ui_support.py.
"""
from __future__ import annotations

import pytest

from tests.system.conftest import artifact_dir, assert_ui_evidence, run_scenario

pytestmark = pytest.mark.ui


@pytest.mark.ui
def test_ui_error_state_keeps_last_screen(ui_instance, ui_node, ui_browser, record_property):
    """Injected API 500 → the UI shows the stale banner and keeps the DOM."""
    record_property("case_id", "ST-UI-007")
    out_dir = artifact_dir() / "ST-UI-007"
    out_dir.mkdir(parents=True, exist_ok=True)
    result = run_scenario(ui_node, {
        "baseUrl": ui_instance.base_url,
        "path": "/ui/",
        "steps": [
            {"action": "waitFor", "expression": "document.querySelectorAll('#tree details').length > 0"},
            {"action": "assert", "expression": "document.querySelector('#tree').textContent.includes('Baseline Deployment B')", "op": "truthy"},
            {"action": "assert", "expression": "document.body.classList.contains('stale')", "op": "falsy"},
            {"action": "eval", "expression": "(()=>{const real=window.fetch;window.__realFetch=real;window.fetch=(u,o)=>String(u).startsWith('/v1')?Promise.resolve(new Response(JSON.stringify({error:{message:'injected failure',code:'injected'}}),{status:500,headers:{'Content-Type':'application/json'}})):real(u,o);return true})()"},
            {"action": "click", "selector": "nav button[data-page='providers']"},
            {"action": "click", "selector": "nav button[data-page='home']"},
            {"action": "waitFor", "expression": "document.body.classList.contains('stale')", "timeoutMs": 5000},
            {"action": "assert", "expression": "document.querySelector('#ui-banner').hidden === false", "op": "truthy"},
            {"action": "assert", "expression": "document.querySelector('#ui-banner').textContent.length > 0", "op": "truthy"},
            {"action": "assert", "expression": "document.querySelectorAll('#tree details').length > 0", "op": "truthy"},
            {"action": "assert", "expression": "document.querySelector('#tree').textContent.includes('Baseline Deployment B')", "op": "truthy"},
            {"action": "eval", "expression": "(()=>{window.fetch=window.__realFetch;return true})()"},
            {"action": "click", "selector": "nav button[data-page='providers']"},
            {"action": "click", "selector": "nav button[data-page='home']"},
            {"action": "waitFor", "expression": "document.body.classList.contains('stale') === false", "timeoutMs": 5000},
            {"action": "waitFor", "expression": "document.querySelectorAll('#tree details').length > 0"},
            {"action": "assert", "expression": "document.querySelector('#tree').textContent.includes('Baseline Deployment B')", "op": "truthy"},
        ],
    }, out_dir, "ST-UI-007")
    assert result["ok"], f"ST-UI-007 failed: {result['failures']}\nnetwork={result['_networkLog']}"
    assert_ui_evidence(result)
