"""ST-UI-010 — real browser-driven UI case (RISK-UI-EXEC-1).

Run:  PYTHONPATH=src python3 -m pytest tests/system/cases/ST-UI-010.py -m ui -q

Pattern: 边界呈现 (boundary rendering). Extreme text must render escaped without
markup injection and without horizontal overflow.
"""
from __future__ import annotations

import json

import pytest

from tests.system.conftest import LLMTierInstance, artifact_dir, assert_ui_evidence, baseline_settings, run_scenario

pytestmark = pytest.mark.ui


@pytest.mark.ui
def test_ui_boundary_long_text_renders_without_overflow(provider_endpoint_b, ui_node, ui_browser, record_property):
    """ST-UI-010 — Pattern: 边界呈现 (boundary rendering)."""
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
            {"action": "assert", "expression": f"document.querySelector('#tree .backend-name b').textContent.includes({expected})", "op": "truthy"},
            {"action": "assert", "expression": "document.querySelectorAll('#tree img').length", "op": "equals", "expected": 0},
            {"action": "assert", "expression": "document.querySelector('#tree .backend-name b').textContent.includes('<img')", "op": "truthy"},
            {"action": "assert", "expression": "document.documentElement.scrollWidth <= window.innerWidth + 2", "op": "truthy"},
            {"action": "screenshot", "name": "boundary"},
        ]
        record_property("case_id", "ST-UI-010")
        out_dir = artifact_dir() / "ST-UI-010"
        out_dir.mkdir(parents=True, exist_ok=True)
        result = run_scenario(ui_node, {
            "baseUrl": inst.base_url, "path": "/ui/", "steps": steps,
        }, out_dir, "ST-UI-010")
        assert result["ok"], f"ST-UI-010 failed: {result['failures']}\nnetwork={result['_networkLog']}"
        assert_ui_evidence(result)
    finally:
        inst.stop()
