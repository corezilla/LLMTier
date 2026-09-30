"""Real browser-driven UI tests — closes ``RISK-UI-EXEC-1``.

Case IDs: UIT-UI-001..007

These cases drive the live ``src/web_ui`` application in a headless Chrome via
CDP (``browser_driver.mjs``) against a **hermetic** temporary LLMTier instance
(B-class, loopback) with the LAN fake provider. They assert **real DOM state and
real network calls**, not source strings — upgrading the previous
``assertIn(app.js, ...)`` contract checks into executed behavior.

Run:
    PYTHONPATH=src python3 -m pytest tests/ui -m ui -q
    # or the documented wrapper:
    tools/run_ui_tests.sh

Artifacts (PNG screenshot + network log per case) are written under
``tests/ui/artifacts/<case>/`` (git-ignored); override with
``LLMTIER_UI_ARTIFACT_DIR``.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from .conftest import run_scenario

pytestmark = pytest.mark.ui

SCENARIOS = [
    # VRC-UI-001 — the page renders (title/tabs present in the live DOM); the
    # provider list is fetched from the API and rendered from that data.
    {
        "id": "UIT-UI-001",
        "vrc": "VRC-UI-001",
        "title": "page renders live and provider rows come from the API",
        "steps": [
            {"action": "assert", "expression": "document.title", "op": "equals", "expected": "LLMTier Console"},
            {"action": "assert", "expression": "document.querySelectorAll('nav button[data-page]').length", "op": "equals", "expected": 5},
            {"action": "assert", "expression": "!!document.querySelector('#home.page.active')", "op": "truthy"},
            {"action": "assert", "expression": "!!document.querySelector('#tree details .tiername')", "op": "truthy"},
            # Providers tab: rows are rendered from `/v1/providers`, not hard-coded.
            {"action": "click", "selector": "nav button[data-page='providers']"},
            {"action": "waitFor", "expression": "document.querySelectorAll('#provider-tree .provider-row').length > 0"},
            {"action": "assert", "expression": "document.querySelector('#provider-tree .providername b').textContent", "op": "equals", "expected": "Baseline Provider B"},
            {"action": "assertNetwork", "urlContains": "/v1/providers", "method": "GET", "status": 200},
        ],
    },
    # VRC-UI-001 — switching tabs changes the visible section and issues the
    # corresponding API calls.
    {
        "id": "UIT-UI-002",
        "vrc": "VRC-UI-001",
        "title": "tab switch toggles the active section and triggers its API call",
        "steps": [
            {"action": "assert", "expression": "document.querySelector('.page.active').id", "op": "equals", "expected": "home"},
            {"action": "click", "selector": "nav button[data-page='stats']"},
            {"action": "assertVisibleSection", "expected": "stats"},
            {"action": "waitFor", "expression": "document.querySelector('#stats-body').children.length > 0"},
            {"action": "assertNetwork", "urlContains": "/v1/stats", "method": "GET", "status": 200},
            {"action": "click", "selector": "nav button[data-page='diagnostics']"},
            {"action": "assertVisibleSection", "expected": "diagnostics"},
            {"action": "waitFor", "expression": "document.querySelectorAll('[data-dtab]').length === 4"},
            # diagnostics sub-tab switch
            {"action": "click", "selector": "[data-dtab='traces']"},
            {"action": "assert", "expression": "document.querySelector('#traces.dsub.active').id", "op": "equals", "expected": "traces"},
            {"action": "assertNetwork", "urlContains": "/v1/diagnostics/traces", "method": "GET", "status": 200},
        ],
    },
    # VRC-UI-003 + VRC-UI-005 — a UI action (confirm-gated) triggers exactly the
    # expected API PATCH/POST, and the DOM updates when the response lands.
    {
        "id": "UIT-UI-003",
        "vrc": "VRC-UI-003",
        "title": "confirm-gated Pause issues If-Match PATCH and the row re-renders",
        "steps": [
            {"action": "eval", "expression": "window.confirm=()=>true"},
            {"action": "waitFor", "expression": "document.querySelectorAll('#tree .backend-toggle').length > 0"},
            # Backend status is rendered as an accessible icon label, not text.
            {"action": "assert", "expression": "document.querySelector('#tree .backend .status-icon').getAttribute('aria-label')", "op": "equals", "expected": "Idle"},
            {"action": "click", "selector": "#tree .backend-toggle"},
            {"action": "waitFor", "expression": "document.querySelector('#tree .backend .status-icon').getAttribute('aria-label') === 'Paused'"},
            {"action": "assertNetwork", "urlContains": "/v1/deployments/", "method": "PATCH", "status": 200},
            # RULE-UI-ETAG: the PATCH carries an If-Match "<id>.v<n>" precondition.
            {"action": "assertRequestHeader", "urlContains": "/v1/deployments/", "method": "PATCH", "header": "If-Match", "matches": "^\"depl_b\\.v[0-9]+\"$"},
            # Resume back so the shared instance stays in its initial state.
            {"action": "click", "selector": "#tree .backend-toggle"},
            {"action": "waitFor", "expression": "document.querySelector('#tree .backend .status-icon').getAttribute('aria-label') === 'Idle'"},
        ],
    },
    # VRC-UI-004 — unknown usage is rendered as unknown/empty, never as 0.
    {
        "id": "UIT-UI-004",
        "vrc": "VRC-UI-004",
        "title": "unknown usage is rendered as unknown/empty, never a fabricated zero",
        "steps": [
            # Providers page: a provider with no usage configured must render the
            # explicit unknown state ("Not refreshed"), not a 0%/0 number.
            {"action": "click", "selector": "nav button[data-page='providers']"},
            {"action": "waitFor", "expression": "document.querySelectorAll('#provider-tree .provider-row').length > 0"},
            {"action": "assert", "expression": "document.querySelector('#provider-tree .provider-row summary .unknown')?.textContent || ''", "op": "includes", "expected": "Not refreshed"},
            # Logs (usage) page: no records must render the empty state, not a
            # zero-filled row table.
            {"action": "click", "selector": "nav button[data-page='logs']"},
            {"action": "assertVisibleSection", "expected": "logs"},
            {"action": "waitFor", "expression": "document.querySelector('#usage-body').children.length > 0"},
            {"action": "assert", "expression": "document.querySelector('#usage-body td[colspan]')?.textContent || ''", "op": "includes", "expected": "No records"},
            # Stats page: empty window must render the empty message.
            {"action": "click", "selector": "nav button[data-page='stats']"},
            {"action": "waitFor", "expression": "document.querySelector('#stats-body').children.length > 0"},
            {"action": "assert", "expression": "document.querySelector('#stats-body td[colspan]')?.textContent || ''", "op": "includes", "expected": "No calls recorded"},
        ],
    },
    # VRC-UI-005 — probe stays an explicit, confirm-gated paid action.
    {
        "id": "UIT-UI-005",
        "vrc": "VRC-UI-005",
        "title": "unconfirmed probe does not touch the network; confirmed probe POSTs",
        "steps": [
            {"action": "eval", "expression": "window.__confirmCount=0;window.confirm=()=>{window.__confirmCount++;return false}"},
            {"action": "waitFor", "expression": "document.querySelectorAll('#tree .backend-probe').length > 0"},
            {"action": "click", "selector": "#tree .backend-probe"},
            {"action": "assert", "expression": "window.__confirmCount", "op": "gte", "expected": 1},
            {"action": "assertNoNetwork", "urlContains": "/v1/probes", "method": "POST"},
            {"action": "eval", "expression": "window.confirm=()=>true"},
            {"action": "click", "selector": "#tree .backend-probe"},
            {"action": "wait", "ms": 400},
            {"action": "assertNetwork", "urlContains": "/v1/probes", "method": "POST", "status": 200},
        ],
    },
    # VRC-UI-006 — diagnostics page 4 tabs render and switch; the OBS visual
    # sub-item (Disabled state actually painted) is asserted from the live DOM.
    {
        "id": "UIT-UI-006",
        "vrc": "VRC-UI-006",
        "title": "diagnostics 4 tabs render/switch and the Disabled state is painted",
        "steps": [
            {"action": "click", "selector": "nav button[data-page='diagnostics']"},
            {"action": "assert", "expression": "document.querySelectorAll('[data-dtab]').length", "op": "equals", "expected": 4},
            {"action": "assert", "expression": "document.querySelector('#snapshots.dsub.active').id", "op": "equals", "expected": "snapshots"},
            # Switches default off -> the snapshots body must show the Disabled
            # row (real render), not an empty/blank table.
            {"action": "waitFor", "expression": "document.querySelector('#snapshots-body').textContent.includes('Disabled')"},
            {"action": "click", "selector": "[data-dtab='dstats']"},
            {"action": "assert", "expression": "document.querySelector('#dstats.dsub.active').id", "op": "equals", "expected": "dstats"},
            {"action": "waitFor", "expression": "document.querySelector('#dstats-body').textContent.includes('Disabled')"},
            {"action": "assertNetwork", "urlContains": "/v1/diagnostics", "method": "GET", "status": 200},
        ],
    },
]


def _artifact_dir() -> Path:
    override = os.environ.get("LLMTIER_UI_ARTIFACT_DIR")
    if override:
        base = Path(override)
    else:
        base = Path(__file__).resolve().parent / "artifacts"
    base.mkdir(parents=True, exist_ok=True)
    return base


@pytest.mark.ui
@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s["id"] for s in SCENARIOS])
def test_ui_scenario(ui_instance, ui_node, ui_browser, scenario, record_property):
    """Drive one UI scenario in a real browser and assert its live behavior."""
    # Case ID for the evidence chain (tools/test_report.py harvests this
    # property; one parametrized module hosts several UI Cases).
    record_property("case_id", scenario["id"])
    out_dir = _artifact_dir() / scenario["id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    result = run_scenario(ui_node, {
        "baseUrl": ui_instance.base_url, "path": "/ui/", "steps": scenario["steps"],
    }, out_dir, scenario["id"])
    assert result["ok"], f"{scenario['id']} failed: {result['failures']}\nnetwork={result['_networkLog']}"
    assert Path(result["_screenshot"]).is_file(), "screenshot artifact missing"


@pytest.mark.ui
def test_ui_error_state_keeps_last_screen(ui_instance, ui_node, ui_browser, record_property):
    """Injected API 500 → the UI shows the stale banner and keeps the DOM.

    This is the ``reportLoadFailure`` / ``dispatchUiError`` behavioral case: the
    page is primed healthy, then the API is forced to fail and the user
    switches tabs; the previous rows must survive and the banner must appear.
    """
    record_property("case_id", "UIT-UI-007")
    out_dir = _artifact_dir() / "UIT-UI-007"
    out_dir.mkdir(parents=True, exist_ok=True)
    result = run_scenario(ui_node, {
        "baseUrl": ui_instance.base_url,
        "path": "/ui/",
        "steps": [
            # Prime a healthy screen so there is a "last screen" to preserve.
            {"action": "waitFor", "expression": "document.querySelectorAll('#tree details').length > 0"},
            {"action": "assert", "expression": "document.querySelector('#tree').textContent.includes('Baseline Deployment B')", "op": "truthy"},
            {"action": "assert", "expression": "document.body.classList.contains('stale')", "op": "falsy"},
            # Force every same-origin API call to fail, then reload Home: the UI
            # must surface the stale banner and keep the rendered tree.
            {"action": "eval", "expression": "(()=>{const real=window.fetch;window.fetch=(u,o)=>String(u).startsWith('/v1')?Promise.resolve(new Response(JSON.stringify({error:{message:'injected failure',code:'injected'}}),{status:500,headers:{'Content-Type':'application/json'}})):real(u,o);return true})()"},
            {"action": "click", "selector": "nav button[data-page='providers']"},
            {"action": "click", "selector": "nav button[data-page='home']"},
            {"action": "waitFor", "expression": "document.body.classList.contains('stale')", "timeoutMs": 5000},
            {"action": "assert", "expression": "document.querySelector('#ui-banner').hidden === false", "op": "truthy"},
            {"action": "assert", "expression": "document.querySelector('#ui-banner').textContent.length > 0", "op": "truthy"},
            # The shell is intact (not blanked) and the tree keeps its last rows.
            {"action": "assert", "expression": "document.querySelectorAll('#tree details').length > 0", "op": "truthy"},
            {"action": "assert", "expression": "document.querySelector('#tree').textContent.includes('Baseline Deployment B')", "op": "truthy"},
        ],
    }, out_dir, "UIT-UI-007")
    assert result["ok"], f"UIT-UI-007 failed: {result['failures']}\nnetwork={result['_networkLog']}"
    assert Path(result["_screenshot"]).is_file(), "screenshot artifact missing"
