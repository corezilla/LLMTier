"""Real browser-driven UI tests — closes ``RISK-UI-EXEC-1``.

Case IDs: ST-UI-001..007

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

import json
import os
from pathlib import Path

import pytest

from .conftest import LLMTierInstance, baseline_settings, run_scenario

pytestmark = pytest.mark.ui

SCENARIOS = [
    # VRC-UI-001 — the page renders (title/tabs present in the live DOM); the
    # provider list is fetched from the API and rendered from that data.
    {
        "id": "ST-UI-001",
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
    # VRC-UI-001 — Pattern: 交互 → 能力调用 (interaction). Clicking a nav tab
    # must issue exactly the expected capability call (method + path + 200) and
    # must NOT issue a call that the current screen does not need (zero-call).
    {
        "id": "ST-UI-002",
        "vrc": "VRC-UI-001",
        "title": "tab switch toggles the active section and triggers its API call",
        "steps": [
            {"action": "assert", "expression": "document.querySelector('.page.active').id", "op": "equals", "expected": "home"},
            # Zero-call: the Home screen must not issue the Stats capability call.
            {"action": "assertNoNetwork", "urlContains": "/v1/stats", "method": "GET"},
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
    # VRC-UI-003 — Pattern: 数据变更（写路径）(data mutation). CONFIRM-gated Pause
    # must flip BOTH sides: the server data really changes (read back via
    # `GET /v1/deployments`) AND the page re-renders with the old value gone.
    {
        "id": "ST-UI-003",
        "vrc": "VRC-UI-003",
        "title": "confirm-gated Pause issues If-Match PATCH and the row re-renders",
        "steps": [
            {"action": "eval", "expression": "window.confirm=()=>true"},
            {"action": "waitFor", "expression": "document.querySelectorAll('#tree .backend-toggle').length > 0"},
            # Backend status is rendered as an accessible icon label, not text.
            {"action": "assert", "expression": "document.querySelector('#tree .backend .status-icon').getAttribute('aria-label')", "op": "equals", "expected": "Idle"},
            # Read-back before the write: the server really has enabled=true.
            {"action": "assert", "expression": "fetch('/v1/deployments').then(r=>r.json()).then(j=>j.data.find(d=>d.id==='depl_b').enabled)", "op": "equals", "expected": True},
            {"action": "screenshot", "name": "before"},
            {"action": "click", "selector": "#tree .backend-toggle"},
            {"action": "waitForNetwork", "urlContains": "/v1/deployments/", "method": "PATCH", "status": 200},
            {"action": "waitFor", "expression": "document.querySelector('#tree .backend .status-icon').getAttribute('aria-label') === 'Paused'"},
            {"action": "assertNetwork", "urlContains": "/v1/deployments/", "method": "PATCH", "status": 200},
            # RULE-UI-ETAG: the PATCH carries an If-Match "<id>.v<n>" precondition.
            {"action": "assertRequestHeader", "urlContains": "/v1/deployments/", "method": "PATCH", "header": "If-Match", "matches": "^\"depl_b\\.v[0-9]+\"$"},
            # Two-sided mutation, side ①: the server data really changed.
            {"action": "assert", "expression": "fetch('/v1/deployments').then(r=>r.json()).then(j=>j.data.find(d=>d.id==='depl_b').enabled)", "op": "equals", "expected": False},
            {"action": "assertNetwork", "urlContains": "/v1/deployments", "method": "GET"},
            # Two-sided mutation, side ②: the page re-rendered — old value gone.
            {"action": "assert", "expression": "document.querySelector('#tree .backend .status-icon').getAttribute('aria-label')", "op": "equals", "expected": "Paused"},
            {"action": "assert", "expression": "!document.querySelector('#tree .backend .status-icon').getAttribute('aria-label').includes('Idle')", "op": "truthy"},
            {"action": "screenshot", "name": "after"},
            # Resume back so the shared instance stays in its initial state; the
            # write path is exercised both directions (Idle -> Paused -> Idle).
            {"action": "eval", "expression": "window.confirm=()=>true"},
            {"action": "click", "selector": "#tree .backend-toggle"},
            {"action": "waitFor", "expression": "document.querySelector('#tree .backend .status-icon').getAttribute('aria-label') === 'Idle'"},
            {"action": "assert", "expression": "fetch('/v1/deployments').then(r=>r.json()).then(j=>j.data.find(d=>d.id==='depl_b').enabled)", "op": "equals", "expected": True},
        ],
    },
    # VRC-UI-004 — Pattern: 数据呈现（渲染）(render). Unknown usage renders as the
    # unknown/empty state, never as a fabricated zero.
    {
        "id": "ST-UI-004",
        "vrc": "VRC-UI-004",
        "title": "unknown usage is rendered as unknown/empty, never a fabricated zero",
        "steps": [
            # Providers page: a provider with no usage configured must render the
            # explicit unknown state ("Not refreshed"), not a 0%/0 number.
            {"action": "click", "selector": "nav button[data-page='providers']"},
            {"action": "waitFor", "expression": "document.querySelectorAll('#provider-tree .provider-row').length > 0"},
            {"action": "assert", "expression": "document.querySelector('#provider-tree .provider-row summary .unknown')?.textContent || ''", "op": "includes", "expected": "Not refreshed"},
            # Negative: the unknown cell must not fabricate a numeric zero.
            {"action": "assert", "expression": "!/\\d/.test(document.querySelector('#provider-tree .provider-row summary .unknown')?.textContent || '')", "op": "truthy"},
            # Logs (usage) page: no records must render the empty state, not a
            # zero-filled row table.
            {"action": "click", "selector": "nav button[data-page='logs']"},
            {"action": "assertVisibleSection", "expected": "logs"},
            {"action": "waitFor", "expression": "document.querySelector('#usage-body').children.length > 0"},
            {"action": "assert", "expression": "document.querySelector('#usage-body td[colspan]')?.textContent || ''", "op": "includes", "expected": "No records"},
            # Negative: the empty state must not render a numeric zero either.
            {"action": "assert", "expression": "!/\\d/.test(document.querySelector('#usage-body td[colspan]')?.textContent || '')", "op": "truthy"},
            # Stats page: empty window must render the empty message.
            {"action": "click", "selector": "nav button[data-page='stats']"},
            {"action": "waitFor", "expression": "document.querySelector('#stats-body').children.length > 0"},
            {"action": "assert", "expression": "document.querySelector('#stats-body td[colspan]')?.textContent || ''", "op": "includes", "expected": "No calls recorded"},
            {"action": "assert", "expression": "!/\\d/.test(document.querySelector('#stats-body td[colspan]')?.textContent || '')", "op": "truthy"},
        ],
    },
    # VRC-UI-005 — Pattern: 门控 / 确认 (gate/confirm). An unconfirmed paid
    # action makes zero calls; a confirmed one POSTs exactly once.
    {
        "id": "ST-UI-005",
        "vrc": "VRC-UI-005",
        "title": "unconfirmed probe does not touch the network; confirmed probe POSTs",
        "steps": [
            {"action": "eval", "expression": "window.__confirmCount=0;window.confirm=()=>{window.__confirmCount++;return false}"},
            {"action": "waitFor", "expression": "document.querySelectorAll('#tree .backend-probe').length > 0"},
            {"action": "click", "selector": "#tree .backend-probe"},
            {"action": "assert", "expression": "window.__confirmCount", "op": "gte", "expected": 1},
            # Zero-call gate: canceling the confirm must not touch the network.
            {"action": "assertNoNetwork", "urlContains": "/v1/probes", "method": "POST"},
            {"action": "eval", "expression": "window.confirm=()=>true"},
            {"action": "click", "selector": "#tree .backend-probe"},
            # Deterministic wait on the network fact (no fixed sleep).
            {"action": "waitForNetwork", "urlContains": "/v1/probes", "method": "POST", "status": 200},
            {"action": "assertNetwork", "urlContains": "/v1/probes", "method": "POST", "status": 200},
            {"action": "assertNetworkCount", "urlContains": "/v1/probes", "method": "POST", "count": 1},
        ],
    },
    # VRC-UI-006 — Pattern: 导航 / 可见性 (navigation). Diagnostics sub-tabs
    # switch the visible section and lazily issue their own call; the Disabled
    # visual is asserted from the live DOM (非空屏, not a source string).
    {
        "id": "ST-UI-006",
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
            # Navigation zero-call: the dstats switch is disabled by default, so
            # selecting that sub-tab must NOT issue the data-plane stats call.
            {"action": "assertNoNetwork", "urlContains": "/v1/diagnostics/stats", "method": "GET"},
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


def _assert_evidence(result: dict) -> None:
    """Every UI Case must emit a PNG screenshot and a network log (constraint)."""
    assert Path(result["_screenshot"]).is_file(), "screenshot artifact missing"
    assert Path(result["_networkLog"]).is_file(), "network log artifact missing"


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
    _assert_evidence(result)



@pytest.mark.ui
def test_ui_error_state_keeps_last_screen(ui_instance, ui_node, ui_browser, record_property):
    """Injected API 500 → the UI shows the stale banner and keeps the DOM.

    This is the ``reportLoadFailure`` / ``dispatchUiError`` behavioral case: the
    page is primed healthy, then the API is forced to fail and the user
    switches tabs; the previous rows must survive and the banner must appear.
    """
    record_property("case_id", "ST-UI-007")
    out_dir = _artifact_dir() / "ST-UI-007"
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
            {"action": "eval", "expression": "(()=>{const real=window.fetch;window.__realFetch=real;window.fetch=(u,o)=>String(u).startsWith('/v1')?Promise.resolve(new Response(JSON.stringify({error:{message:'injected failure',code:'injected'}}),{status:500,headers:{'Content-Type':'application/json'}})):real(u,o);return true})()"},
            {"action": "click", "selector": "nav button[data-page='providers']"},
            {"action": "click", "selector": "nav button[data-page='home']"},
            {"action": "waitFor", "expression": "document.body.classList.contains('stale')", "timeoutMs": 5000},
            {"action": "assert", "expression": "document.querySelector('#ui-banner').hidden === false", "op": "truthy"},
            {"action": "assert", "expression": "document.querySelector('#ui-banner').textContent.length > 0", "op": "truthy"},
            # The shell is intact (not blanked) and the tree keeps its last rows.
            {"action": "assert", "expression": "document.querySelectorAll('#tree details').length > 0", "op": "truthy"},
            {"action": "assert", "expression": "document.querySelector('#tree').textContent.includes('Baseline Deployment B')", "op": "truthy"},
            # Recovery: once the API is healthy again, a retry renders normally
            # and the stale marker is gone (degradation is recoverable).
            {"action": "eval", "expression": "(()=>{window.fetch=window.__realFetch;return true})()"},
            {"action": "click", "selector": "nav button[data-page='providers']"},
            {"action": "click", "selector": "nav button[data-page='home']"},
            {"action": "waitFor", "expression": "document.body.classList.contains('stale') === false", "timeoutMs": 5000},
            {"action": "waitFor", "expression": "document.querySelectorAll('#tree details').length > 0"},
            {"action": "assert", "expression": "document.querySelector('#tree').textContent.includes('Baseline Deployment B')", "op": "truthy"},
        ],
    }, out_dir, "ST-UI-007")
    assert result["ok"], f"ST-UI-007 failed: {result['failures']}\nnetwork={result['_networkLog']}"
    _assert_evidence(result)


def _run_custom_scenario(ui_node, inst, steps, case_id, record_property):
    """Run one scenario against a caller-owned instance and assert the evidence."""
    record_property("case_id", case_id)
    out_dir = _artifact_dir() / case_id
    out_dir.mkdir(parents=True, exist_ok=True)
    result = run_scenario(ui_node, {
        "baseUrl": inst.base_url, "path": "/ui/", "steps": steps,
    }, out_dir, case_id)
    assert result["ok"], f"{case_id} failed: {result['failures']}\nnetwork={result['_networkLog']}"
    _assert_evidence(result)
    return out_dir, result


@pytest.mark.ui
def test_ui_provider_secret_never_shown(provider_endpoint_b, ui_node, ui_browser, record_property):
    """ST-UI-008 — Pattern: 脱敏 / 安全呈现 (redaction).

    A provider configured with a secret reference must render only the
    redaction marker (``Configured``): the secret VALUE and the reference
    STRING must never appear in the live DOM, the page URL, the edit form, or
    the captured network log.
    """
    secret_ref = "env:LLMTIER_UI_SECRET_008"
    secret_value = "SUPERSECRET_008_VALUE"
    settings = baseline_settings(provider_endpoint_b)
    settings["providers"].append({
        "id": "prov_secret", "name": "Secret Provider 008", "kind": "cloud",
        "endpoint": provider_endpoint_b, "secret_ref": secret_ref, "enabled": True,
    })
    inst = LLMTierInstance(settings, extra_env={"LLMTIER_UI_SECRET_008": secret_value})
    inst.start()
    try:
        steps = [
            {"action": "click", "selector": "nav button[data-page='providers']"},
            {"action": "waitFor", "expression": "document.querySelectorAll('#provider-tree .provider-row').length >= 2"},
            # The secret provider renders the redaction marker, not the value.
            {"action": "assert", "expression": "(()=>{const rows=[...document.querySelectorAll('#provider-tree .provider-row')];const row=rows.find(r=>r.textContent.includes('Secret Provider 008'));return row?row.textContent.includes('Configured'):false})()", "op": "truthy"},
            # Open the edit drawer: the secret_ref input must never be prefilled.
            {"action": "assert", "expression": "(()=>{const btn=[...document.querySelectorAll('.provider-edit')].find(b=>b.dataset.provider==='prov_secret');if(!btn)return false;btn.click();return true})()", "op": "truthy"},
            {"action": "waitFor", "expression": "document.querySelector('#provider-mask').classList.contains('open')"},
            {"action": "assert", "expression": "document.querySelector('#provider-form').elements.secret_ref.value === ''", "op": "truthy"},
            # DOM-wide scan: neither the value nor the reference may leak.
            {"action": "assert", "expression": f"!document.documentElement.outerHTML.includes({json.dumps(secret_value)})", "op": "truthy"},
            {"action": "assert", "expression": f"!document.documentElement.outerHTML.includes({json.dumps(secret_ref)})", "op": "truthy"},
            {"action": "assert", "expression": f"!location.href.includes({json.dumps(secret_value)}) && !location.href.includes({json.dumps(secret_ref)})", "op": "truthy"},
        ]
        out_dir, result = _run_custom_scenario(ui_node, inst, steps, "ST-UI-008", record_property)
        # Network-log scan: the value/reference must not appear in any recorded
        # URL or request header either.
        log = Path(result["_networkLog"]).read_text(encoding="utf-8")
        assert secret_value not in log, "secret value leaked into the network log"
        assert secret_ref not in log, "secret reference leaked into the network log"
    finally:
        inst.stop()


@pytest.mark.ui
def test_ui_double_click_probe_is_not_duplicated(ui_instance, ui_node, ui_browser, record_property):
    """ST-UI-009 — Pattern: 幂等 / 防重 (idempotency).

    A rapid double activation of the confirm-gated Probe button must produce
    exactly ONE ``POST /v1/probes`` and must not append duplicate rows: the
    in-flight button is disabled synchronously, so the second click is a no-op.
    """
    steps = [
        {"action": "eval", "expression": "window.confirm=()=>true"},
        {"action": "waitFor", "expression": "document.querySelectorAll('#tree .backend-probe').length > 0"},
        {"action": "assert", "expression": "document.querySelectorAll('#tree details').length", "op": "equals", "expected": 7},
        # Two clicks in the same task, before the first request settles.
        {"action": "eval", "expression": "(()=>{const b=document.querySelector('#tree .backend-probe');b.click();b.click();return true})()"},
        {"action": "waitForNetwork", "urlContains": "/v1/probes", "method": "POST", "status": 200},
        {"action": "assertNetwork", "urlContains": "/v1/probes", "method": "POST", "status": 200},
        # Idempotency: exactly one effective call, and the tree did not grow.
        {"action": "assertNetworkCount", "urlContains": "/v1/probes", "method": "POST", "count": 1},
        {"action": "assert", "expression": "document.querySelectorAll('#tree details').length", "op": "equals", "expected": 7},
    ]
    _run_custom_scenario(ui_node, ui_instance, steps, "ST-UI-009", record_property)


@pytest.mark.ui
def test_ui_boundary_long_text_renders_without_overflow(provider_endpoint_b, ui_node, ui_browser, record_property):
    """ST-UI-010 — Pattern: 边界呈现 (boundary rendering).

    Extreme text (very long name + HTML metacharacters) must render exactly as
    escaped text without injecting markup and without causing horizontal page
    overflow — the boundary input does not break the layout.
    """
    long_text = "L" + ("X" * 300) + "<img src=x onerror=alert(1)> & \"quoted\""
    settings = baseline_settings(provider_endpoint_b)
    settings["deployments"][0]["name"] = long_text
    settings["deployments"][0]["backend_model"] = long_text
    inst = LLMTierInstance(settings)
    inst.start()
    try:
        expected = json.dumps(long_text)
        steps = [
            {"action": "waitFor", "expression": "document.querySelectorAll('#tree details').length > 0"},
            # The exact boundary string is present as text…
            {"action": "assert", "expression": f"document.querySelector('#tree .backend-name b').textContent.includes({expected})", "op": "truthy"},
            # …and is escaped, not parsed into markup (no injected <img>).
            {"action": "assert", "expression": "document.querySelectorAll('#tree img').length", "op": "equals", "expected": 0},
            {"action": "assert", "expression": "document.querySelector('#tree .backend-name b').textContent.includes('<img')", "op": "truthy"},
            # No horizontal overflow: long text must wrap, not widen the page.
            {"action": "assert", "expression": "document.documentElement.scrollWidth <= window.innerWidth + 2", "op": "truthy"},
            {"action": "screenshot", "name": "boundary"},
        ]
        _run_custom_scenario(ui_node, inst, steps, "ST-UI-010", record_property)
    finally:
        inst.stop()

