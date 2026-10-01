"""ST-UI-008 — real browser-driven UI case (RISK-UI-EXEC-1).

Run:  PYTHONPATH=src python3 -m pytest tests/system/cases/ST-UI-008.py -m ui -q

Pattern: 脱敏 / 安全呈现 (redaction). A provider with a secret reference renders
only the redaction marker; the value/reference never leak into DOM/URL/network.
Fixtures live in tests/system/conftest.py; the runner in
tests/common/drivers/ui_support.py.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.system.conftest import LLMTierInstance, artifact_dir, assert_ui_evidence, baseline_settings, run_scenario

pytestmark = pytest.mark.ui


@pytest.mark.ui
def test_ui_provider_secret_never_shown(provider_endpoint_b, ui_node, ui_browser, record_property):
    """ST-UI-008 — Pattern: 脱敏 / 安全呈现 (redaction)."""
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
            {"action": "assert", "expression": "(()=>{const rows=[...document.querySelectorAll('#provider-tree .provider-row')];const row=rows.find(r=>r.textContent.includes('Secret Provider 008'));return row?row.textContent.includes('Configured'):false})()", "op": "truthy"},
            {"action": "assert", "expression": "(()=>{const btn=[...document.querySelectorAll('.provider-edit')].find(b=>b.dataset.provider==='prov_secret');if(!btn)return false;btn.click();return true})()", "op": "truthy"},
            {"action": "waitFor", "expression": "document.querySelector('#provider-mask').classList.contains('open')"},
            {"action": "assert", "expression": "document.querySelector('#provider-form').elements.secret_ref.value === ''", "op": "truthy"},
            {"action": "assert", "expression": f"!document.documentElement.outerHTML.includes({json.dumps(secret_value)})", "op": "truthy"},
            {"action": "assert", "expression": f"!document.documentElement.outerHTML.includes({json.dumps(secret_ref)})", "op": "truthy"},
            {"action": "assert", "expression": f"!location.href.includes({json.dumps(secret_value)}) && !location.href.includes({json.dumps(secret_ref)})", "op": "truthy"},
        ]
        record_property("case_id", "ST-UI-008")
        out_dir = artifact_dir() / "ST-UI-008"
        out_dir.mkdir(parents=True, exist_ok=True)
        result = run_scenario(ui_node, {
            "baseUrl": inst.base_url, "path": "/ui/", "steps": steps,
        }, out_dir, "ST-UI-008")
        assert result["ok"], f"ST-UI-008 failed: {result['failures']}\nnetwork={result['_networkLog']}"
        assert_ui_evidence(result)
        log = Path(result["_networkLog"]).read_text(encoding="utf-8")
        assert secret_value not in log, "secret value leaked into the network log"
        assert secret_ref not in log, "secret reference leaked into the network log"
    finally:
        inst.stop()
