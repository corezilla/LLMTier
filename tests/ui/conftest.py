"""B-class fixtures for the real-browser UI tests (RISK-UI-EXEC-1 closure).

Dependency declaration (TS-002) and LAN constraint (TS-003):

  * LLMTier under test : a **hermetic** temporary ``LLMTierInstance`` bound to
    ``127.0.0.1:<ephemeral>`` (the B-class fixture from
    ``tests/system/api_test_v03/conftest.py``).  m5air is **not** used.
  * Upstream provider  : the LAN-bound fake provider
    (``tests/fixtures/v03_fake_provider.py``) on the detected LAN IP
    (``192.168.x.x``), never ``127.0.0.1`` — ``TS-003``.
  * Browser            : headless Chrome / chrome-headless-shell resolved from
    ``LLMTIER_BROWSER`` or a known cache path (see ``browser_driver.mjs``).
    Nothing is downloaded at test time.

The UI is served by LLMTier itself on the same origin (``/ui/``), so the browser
talks to the temporary instance only; no host outside loopback is contacted by
the page.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Generator

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
UI_DIR = Path(__file__).resolve().parent
DRIVER = UI_DIR / "browser_driver.mjs"

# Reuse the canonical B-class harness (instance lifecycle + LAN fake provider).
# Loaded by file path to avoid colliding with this module's own name `conftest`.
import importlib.util  # noqa: E402

_B_CONFTEST = REPO_ROOT / "tests" / "system" / "api_test_v03" / "conftest.py"
_spec = importlib.util.spec_from_file_location("llmtier_b_conftest", _B_CONFTEST)
_b = importlib.util.module_from_spec(_spec)
sys.modules["llmtier_b_conftest"] = _b
_spec.loader.exec_module(_b)
LLMTierInstance = _b.LLMTierInstance


def _node_binary() -> str:
    override = os.environ.get("LLMTIER_NODE")
    if override:
        return override
    nvm = Path.home() / ".nvm" / "versions" / "node"
    if nvm.is_dir():
        candidates = sorted(nvm.glob("v*/bin/node"), reverse=True)
        if candidates:
            return str(candidates[0])
    return "node"


def _browser_available() -> tuple[bool, str]:
    # Probe by asking node to resolve the same candidate list the driver uses.
    node = _node_binary()
    if not _which(node):
        return False, f"node not runnable: {node}"
    script = (
        "import fs from 'node:fs';import os from 'node:os';import path from 'node:path';"
        "const c=[process.env.LLMTIER_BROWSER,"
        "'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',"
        "path.join(os.homedir(),'.cache/puppeteer/chrome/mac-1108766/chrome-mac/Chromium.app/Contents/MacOS/Chromium'),"
        "path.join(os.homedir(),'Library/Caches/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-mac-arm64/chrome-headless-shell')"
        "].filter(Boolean);const f=c.find(x=>{try{return fs.existsSync(x)}catch{return false}});"
        "process.stdout.write(f||'');"
    )
    try:
        out = subprocess.run([node, "--input-type=module", "-e", script], capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"browser probe failed: {exc}"
    path = out.stdout.strip()
    return (bool(path), path or "no browser executable found")


def _which(binary: str) -> str | None:
    if os.path.sep in binary:
        return binary if os.access(binary, os.X_OK) else None
    for part in os.environ.get("PATH", "").split(os.pathsep):
        candidate = os.path.join(part, binary)
        if os.access(candidate, os.X_OK):
            return candidate
    return None


@pytest.fixture(scope="session")
def ui_browser() -> str:
    ok, detail = _browser_available()
    if not ok:
        pytest.skip(f"UI browser unavailable ({detail}); set LLMTIER_BROWSER")
    return detail


@pytest.fixture(scope="session")
def ui_node() -> str:
    node = _node_binary()
    if not _which(node):
        pytest.skip(f"node unavailable ({node}); set LLMTIER_NODE")
    return node


@pytest.fixture(scope="session")
def fake_provider_b() -> Generator["_b._FakeProvider", None, None]:
    """The LAN-bound fake upstream for the UI cases (TS-003).

    Re-declared here (rather than importing the B-class fixture object) because
    pytest only discovers fixtures defined in a conftest reachable from the test
    path; the helper classes are still the canonical B-class ones.
    """
    if os.environ.get("LLMTIER_TEST_PROVIDER_URL"):
        pytest.skip("LLMTIER_TEST_PROVIDER_URL set: fake provider control unavailable")
    lan_ip = _b._detect_lan_ip()
    if not lan_ip:
        pytest.skip("TS-003: no LAN IP available for the UI fake upstream provider")
    provider = _b._FakeProvider(lan_ip, _b._find_free_port(lan_ip))
    provider.start()
    try:
        yield provider
    finally:
        provider.stop()


@pytest.fixture(scope="session")
def provider_endpoint_b(fake_provider_b: "_b._FakeProvider") -> str:
    """LAN-IP upstream URL for the UI baseline provider (TS-003)."""
    return fake_provider_b.url


@pytest.fixture(scope="session")
def ui_instance(provider_endpoint_b: str) -> Generator[LLMTierInstance, None, None]:
    """A hermetic baseline LLMTier instance (1 provider, 1 deployment, 7 tiers).

    ``provider_endpoint_b`` is the LAN fake-provider URL (TS-003). The instance
    serves both the API and the static UI on the same loopback origin.
    """
    inst = LLMTierInstance(_b._baseline_settings(provider_endpoint_b))
    inst.start()
    # Probe the baseline deployment so `/readyz` reports `ready` and the Home
    # page renders the tier tree with a healthy backend status (mirrors
    # ``llmtier_b``). Without this the UI would render the degraded/unprobed
    # state and the tab/row assertions would be testing the wrong screen.
    status = _b._probe_deployment(inst, "depl_b")
    assert status == "healthy", f"UI baseline depl_b probe not healthy: {status}"
    yield inst
    inst.stop()


def run_scenario(node: str, scenario: dict, tmp_dir: Path, name: str) -> dict:
    """Run one scenario through the CDP driver and return its JSON verdict.

    Self-cleaning: the driver kills the browser and removes its profile in a
    ``finally``; the scenario config lives in a temp dir removed here. Only the
    screenshot and network log are kept (as artifacts).
    """
    cfg_dir = Path(tempfile.mkdtemp(prefix="llmtier-ui-cfg-"))
    config_path = cfg_dir / f"{name}.config.json"
    screenshot = tmp_dir / f"{name}.png"
    network_log = tmp_dir / f"{name}.network.json"
    scenario = dict(scenario)
    scenario["screenshot"] = str(screenshot)
    scenario["networkLog"] = str(network_log)
    config_path.write_text(json.dumps(scenario), encoding="utf-8")

    try:
        proc = subprocess.run(
            [node, str(DRIVER), "--config", str(config_path)],
            capture_output=True, text=True, timeout=180, cwd=str(REPO_ROOT),
        )
    finally:
        shutil.rmtree(cfg_dir, ignore_errors=True)
    raw = proc.stdout.strip()
    if not raw:
        raise AssertionError(f"UI driver produced no output (stderr: {proc.stderr[-800:]})")
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"UI driver output not JSON: {exc}: {raw[:500]} (stderr: {proc.stderr[-500:]})")
    result["_screenshot"] = str(screenshot)
    result["_networkLog"] = str(network_log)
    return result
