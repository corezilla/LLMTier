"""Real-browser UI test support (STD 78876c9: driver under ``tests/common/drivers``).

The 10 UI cases (``tests/system/cases/ST-UI-001..010.py``) drive the live
``src/web_ui`` application in a headless Chrome via CDP
(``tests/common/drivers/browser_driver.mjs``) against a **hermetic** temporary
LLMTier instance (loopback) with the LAN fake provider.

This module holds the node/browser resolution and the scenario runner; the
pytest fixtures live in ``tests/system/conftest.py`` (discovered for every case
under ``tests/system/``).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DRIVER = Path(__file__).resolve().parent / "browser_driver.mjs"


def node_binary() -> str:
    override = os.environ.get("LLMTIER_NODE")
    if override:
        return override
    nvm = Path.home() / ".nvm" / "versions" / "node"
    if nvm.is_dir():
        candidates = sorted(nvm.glob("v*/bin/node"), reverse=True)
        if candidates:
            return str(candidates[0])
    return "node"


def which(binary: str) -> str | None:
    if os.path.sep in binary:
        return binary if os.access(binary, os.X_OK) else None
    for part in os.environ.get("PATH", "").split(os.pathsep):
        candidate = os.path.join(part, binary)
        if os.access(candidate, os.X_OK):
            return candidate
    return None


def browser_available() -> tuple[bool, str]:
    node = node_binary()
    if not which(node):
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


def artifact_dir() -> Path:
    override = os.environ.get("LLMTIER_UI_ARTIFACT_DIR")
    base = Path(override) if override else REPO_ROOT / "tests" / "system" / "artifacts"
    base.mkdir(parents=True, exist_ok=True)
    return base


def run_scenario(node: str, scenario: dict, tmp_dir: Path, name: str) -> dict:
    """Run one scenario through the CDP driver and return its JSON verdict."""
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


def assert_evidence(result: dict) -> None:
    assert Path(result["_screenshot"]).is_file(), "screenshot artifact missing"
    assert Path(result["_networkLog"]).is_file(), "network log artifact missing"
