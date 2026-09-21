"""A 类 conftest — m5air 现有实例直接连。

依赖（TS-002）：
  Endpoint: http://192.168.1.9:8181
  Auth: Bearer dev-data / dev-admin
  上游: m5air OMLX 9000, m5mac OMLX 9000

B 类 fixtures（_b suffix）—— 临时 LLMTier 实例（session-scope）：
  llmtier_b: 基线实例（prov_b + depl_b）
  llmtier_b_empty: 空实例（无任何资源）
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Generator

import httpx
import pytest

M5AIR_BASE = "http://192.168.1.9:8181"
M5AIR_OMLX = "http://192.168.1.9:9000/v1"
M5MAC_OMLX = "http://192.168.1.8:9000/v1"
OMLX_TOKEN = "9832"

FIXED_TIERS = ("Senior", "Junior", "Worker", "Associate", "Engineer", "Executor", "Embedding-v1")


def _http_status(url: str, headers: dict | None = None, timeout: float = 5.0) -> tuple[int, str]:
    try:
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"


def _check_m5air_healthz() -> tuple[bool, str]:
    status, body = _http_status(f"{M5AIR_BASE}/healthz")
    if status != 200:
        return False, f"/healthz returned {status}: {body[:120]}"
    try:
        data = json.loads(body)
        if data.get("status") != "ok":
            return False, f"/healthz status field != 'ok': {data}"
    except json.JSONDecodeError as e:
        return False, f"/healthz body not JSON: {e}"
    return True, "ok"


def _check_m5air_readyz() -> tuple[bool, str]:
    status, body = _http_status(f"{M5AIR_BASE}/readyz")
    if status != 200:
        return False, f"/readyz returned {status}: {body[:120]}"
    try:
        data = json.loads(body)
        models = data.get("models") or data.get("tiers") or []
        ids = {m.get("id") if isinstance(m, dict) else m for m in models}
        missing = set(FIXED_TIERS) - ids
        if missing:
            return False, f"/readyz missing tiers: {sorted(missing)}"
    except json.JSONDecodeError as e:
        return False, f"/readyz body not JSON: {e}"
    return True, f"ok ({len(models)} models)"


def _check_omlx(url: str, name: str) -> tuple[bool, str]:
    status, body = _http_status(url + "/models", {"Authorization": f"Bearer {OMLX_TOKEN}"})
    if status != 200:
        return False, f"{name} OMLX /models returned {status}: {body[:120]}"
    return True, "ok"


def _check_provider_omlx_m5mac_secret_ref() -> tuple[bool, str]:
    req = urllib.request.Request(
        f"{M5AIR_BASE}/tier/admin/v1/providers/provider_omlx_m5mac",
        headers={"Authorization": "Bearer dev-admin"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return False, f"/providers/provider_omlx_m5mac returned {e.code}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"
    if not data.get("has_secret"):
        return False, "provider_omlx_m5mac.has_secret=False (expect True)"
    return True, "ok (has_secret=True)"


_CHECKS = [
    ("§2.1.1 m5air LLMTier /healthz 200", _check_m5air_healthz),
    ("§2.1.2 m5air LLMTier /readyz 200 + 7 tier", _check_m5air_readyz),
    ("§2.1.3 m5air OMLX 9000 健康", lambda: _check_omlx(M5AIR_OMLX, "m5air")),
    ("§2.1.4 m5mac OMLX 9000 健康", lambda: _check_omlx(M5MAC_OMLX, "m5mac")),
    ("§2.1.5 provider_omlx_m5mac.secret_ref = file: 路径", _check_provider_omlx_m5mac_secret_ref),
]


def pytest_report_header(config):
    lines = ["A 类 API 测试套件 — m5air 直连"]
    for label, fn in _CHECKS:
        try:
            ok, detail = fn()
            mark = "OK" if ok else "FAIL"
            lines.append(f"  [{mark}] {label} — {detail}")
        except Exception as e:
            lines.append(f"  [ERR] {label} — {type(e).__name__}: {e}")
    return lines


def pytest_configure(config):
    failed = []
    for label, fn in _CHECKS:
        try:
            ok, detail = fn()
            if not ok:
                failed.append(f"{label}: {detail}")
        except Exception as e:
            failed.append(f"{label}: {type(e).__name__}: {e}")

    if failed:
        msg = "§2.1 环境就绪检查失败，整个 A 类 suite skip:\n  " + "\n  ".join(failed)
        config._env_checks_failed = msg


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    if not getattr(config, "_env_checks_failed", None):
        return
    skip = pytest.mark.skip(reason=f"§2.1 check failed: {config._env_checks_failed}")
    for item in items:
        item.add_marker(skip)


@pytest.fixture(scope="session")
def m5air_base_url() -> str:
    return M5AIR_BASE


@pytest.fixture(scope="session")
def api_client() -> httpx.Client:
    return httpx.Client(
        base_url=M5AIR_BASE,
        headers={"Authorization": "Bearer dev-data"},
        timeout=httpx.Timeout(30.0, connect=5.0),
    )


@pytest.fixture(scope="session")
def admin_client() -> httpx.Client:
    return httpx.Client(
        base_url=M5AIR_BASE,
        headers={"Authorization": "Bearer dev-admin"},
        timeout=httpx.Timeout(30.0, connect=5.0),
    )


def parse_sse(response: httpx.Response) -> list[dict]:
    """解析 SSE 流，yield 每个 event 完整 payload（含 event 名与 data JSON）。"""
    events = []
    event_name = None
    data_buf: list[str] = []
    for raw in response.iter_lines():
        if raw is None:
            continue
        line = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
        if line.startswith("event:"):
            event_name = line[len("event:"):].strip()
        elif line.startswith("data:"):
            data_buf.append(line[len("data:"):].strip())
        elif line == "":
            if event_name and data_buf:
                payload_str = "\n".join(data_buf)
                try:
                    payload = json.loads(payload_str)
                except json.JSONDecodeError:
                    payload = {"_raw": payload_str}
                events.append({"event": event_name, "data": payload})
            event_name = None
            data_buf = []
    return events


def parse_sse_raw(response: httpx.Response) -> list[tuple[str, dict]]:
    """同 parse_sse 但返回 (event_name, data) 元组。"""
    return [(e["event"], e["data"]) for e in parse_sse(response)]


# ---------------------------------------------------------------------------
# B-class fixtures — 临时 LLMTier 实例（session-scope）
# ---------------------------------------------------------------------------

def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class LLMTierInstance:
    """Manage a temporary LLMTier v0.3 process with an isolated SQLite DB."""

    def __init__(self, settings: dict | None = None, dev_mode: bool = True):
        self.port = _find_free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        self._tmpdir = Path(tempfile.mkdtemp(prefix="llmtier_b_"))
        self._db_path = self._tmpdir / "test.sqlite3"
        self._settings_path = self._tmpdir / "settings.json"

        if settings is not None:
            self._settings_path.write_text(json.dumps(settings))

        env = os.environ.copy()
        if dev_mode:
            env["LLMTIER_DEV_MODE"] = "1"
        env["LLMTIER_DATABASE"] = str(self._db_path)
        env["PYTHONPATH"] = "src"
        if settings is not None:
            env["LLMTIER_SETTINGS"] = str(self._settings_path)

        self._proc = subprocess.Popen(
            [sys.executable, "-m", "llmtier_v03",
             "--host", "127.0.0.1",
             "--port", str(self.port)],
            env=env,
            cwd="/Users/ben/work/LLMTier",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def start(self) -> None:
        for _ in range(40):
            try:
                req = urllib.request.Request(f"{self.base_url}/healthz")
                with urllib.request.urlopen(req, timeout=2) as resp:
                    if resp.status == 200:
                        return
            except (urllib.error.URLError, socket.error, OSError):
                pass
            time.sleep(0.25)
        raise RuntimeError(f"LLMTier did not become healthy on port {self.port}")

    def stop(self) -> None:
        if self._proc is not None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait()
            self._proc = None
        try:
            import shutil
            shutil.rmtree(self._tmpdir)
        except OSError:
            pass

    def admin_client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": "Bearer dev-admin"},
            timeout=httpx.Timeout(30.0, connect=5.0),
        )

    def api_client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": "Bearer dev-data"},
            timeout=httpx.Timeout(30.0, connect=5.0),
        )


_BASELINE_SETTINGS = {
    "providers": [
        {
            "id": "prov_b",
            "name": "Baseline Provider B",
            "kind": "local",
            "endpoint": "http://127.0.0.1:9000/v1",
            "secret_ref": None,
            "enabled": True,
        }
    ],
    "deployments": [
        {
            "id": "depl_b",
            "name": "Baseline Deployment B",
            "provider_id": "prov_b",
            "backend_model": "test-model",
            "capabilities": {
                "responses": True,
                "embeddings": False,
                "tools": False,
                "structured_outputs": False,
                "input_modalities": ["text"],
                "output_modalities": ["text"],
                "context_window": 4096,
                "max_output_tokens": 2048,
                "embedding_space_id": None,
                "embedding_dimensions": None,
                "embedding_max_batch_inputs": None,
                "embedding_max_input_tokens": None,
            },
            "enabled": True,
        }
    ],
    "service_levels": [
        {"id": tier, "deployment_ids": ["depl_b"], "enabled": True}
        for tier in ("Senior", "Junior", "Worker", "Associate", "Engineer", "Executor", "Embedding-v1")
    ],
}

_EMPTY_SETTINGS = {
    "providers": [],
    "deployments": [],
    "service_levels": [],
}

_NO_AUTH_SETTINGS = {
    "providers": [],
    "deployments": [],
    "service_levels": [],
}


@pytest.fixture(scope="session")
def llmtier_b() -> Generator[LLMTierInstance, None, None]:
    inst = LLMTierInstance(_BASELINE_SETTINGS)
    inst.start()
    yield inst
    inst.stop()


@pytest.fixture(scope="session")
def llmtier_b_empty() -> Generator[LLMTierInstance, None, None]:
    inst = LLMTierInstance(_EMPTY_SETTINGS)
    inst.start()
    yield inst
    inst.stop()


@pytest.fixture(scope="session")
def base_url_b(llmtier_b: LLMTierInstance) -> str:
    return llmtier_b.base_url


@pytest.fixture(scope="session")
def admin_client_b(llmtier_b: LLMTierInstance) -> Generator[httpx.Client, None, None]:
    client = llmtier_b.admin_client()
    yield client
    client.close()


@pytest.fixture(scope="session")
def api_client_b(llmtier_b: LLMTierInstance) -> Generator[httpx.Client, None, None]:
    client = llmtier_b.api_client()
    yield client
    client.close()


@pytest.fixture(scope="session")
def admin_client_b_empty(llmtier_b_empty: LLMTierInstance) -> Generator[httpx.Client, None, None]:
    client = llmtier_b_empty.admin_client()
    yield client
    client.close()


@pytest.fixture(scope="session")
def llmtier_b_no_auth() -> Generator[LLMTierInstance, None, None]:
    inst = LLMTierInstance(_NO_AUTH_SETTINGS, dev_mode=False)
    inst.start()
    yield inst
    inst.stop()


@pytest.fixture(scope="session")
def admin_client_b_no_auth(llmtier_b_no_auth: LLMTierInstance) -> Generator[httpx.Client, None, None]:
    client = llmtier_b_no_auth.admin_client()
    yield client
    client.close()
