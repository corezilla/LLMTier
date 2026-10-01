"""A 类 conftest — m5air 现有实例直接连。

依赖（TS-002）：
  Endpoint: http://192.168.1.9:8181
  Auth: Bearer dev-data / dev-admin
  上游: m5air OMLX 9000, m5mac OMLX 9000

B 类 fixtures（_b suffix）—— 临时 LLMTier 实例（session-scope）：
  llmtier_b: 基线实例（prov_b + depl_b）
  llmtier_b_empty: 空实例（无任何资源）

TS-003：B 类上游 provider 的 *endpoint* 必须是 LAN IP。conftest 在
机器 LAN IP 上起一个 fake provider（`tests/fixtures/models/v03_fake_provider.py`），
或用 `LLMTIER_TEST_PROVIDER_URL` 指定一个 LAN URL；绝不用 127.0.0.1/localhost。
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

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
FAKE_PROVIDER_SCRIPT = REPO_ROOT / "tests" / "fixtures" / "models" / "v03_fake_provider.py"

M5AIR_BASE = "http://192.168.1.9:8181"
M5AIR_OMLX = "http://192.168.1.9:9000/v1"
M5MAC_OMLX = "http://192.168.1.8:9000/v1"
OMLX_TOKEN = "9832"

FIXED_TIERS = ("Senior", "Junior", "Worker", "Associate", "Engineer", "Executor", "Embedding-v1")

REQUIRED_A_PROVIDERS = ("provider_local", "provider_minimax", "provider_omlx_m5mac")
REQUIRED_A_DEPLOYMENTS = ("dep_local_gemma", "dep_local_bge_m3", "dep_omlx_qwen36", "dep_minimax_m27")

PYTHON = os.environ.get("LLMTIER_TEST_PYTHON", sys.executable)


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
        if not isinstance(data.get("version"), str):
            return False, f"/healthz version field not a string: {data}"
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
        f"{M5AIR_BASE}/v1/providers/provider_omlx_m5mac",
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


def _check_required_a_resources() -> tuple[bool, str]:
    """§2.1.6 — A 类依赖的 m5air provider / deployment 必须实际存在。"""
    headers = {"Authorization": "Bearer dev-admin"}
    for pid in REQUIRED_A_PROVIDERS:
        status, _ = _http_status(f"{M5AIR_BASE}/v1/providers/{pid}", headers)
        if status != 200:
            return False, f"provider {pid} missing (HTTP {status})"
    for did in REQUIRED_A_DEPLOYMENTS:
        status, _ = _http_status(f"{M5AIR_BASE}/v1/deployments/{did}", headers)
        if status != 200:
            return False, f"deployment {did} missing (HTTP {status})"
    return True, f"ok ({len(REQUIRED_A_PROVIDERS)} providers, {len(REQUIRED_A_DEPLOYMENTS)} deployments)"


_CHECKS = [
    ("§2.1.1 m5air LLMTier /healthz 200", _check_m5air_healthz),
    ("§2.1.2 m5air LLMTier /readyz 200 + 7 tier", _check_m5air_readyz),
    ("§2.1.3 m5air OMLX 9000 健康", lambda: _check_omlx(M5AIR_OMLX, "m5air")),
    ("§2.1.4 m5mac OMLX 9000 健康", lambda: _check_omlx(M5MAC_OMLX, "m5mac")),
    ("§2.1.5 provider_omlx_m5mac 已注册且 has_secret=true（secret_ref 只写不返回）", _check_provider_omlx_m5mac_secret_ref),
    ("§2.1.6 必需 provider/deployment 已注册", _check_required_a_resources),
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
    # §2.1 就绪检查只覆盖 A 类（m5air 已部署实例）。A 与 B 独立（§2.3/§2.9）：
    # readiness 失败只 skip A 类（api_a）用例；B 类（api_b）用各自临时实例，仍须执行。
    skip = pytest.mark.skip(reason=f"§2.1 check failed: {config._env_checks_failed}")
    for item in items:
        if item.get_closest_marker("api_b") is not None:
            continue
        item.add_marker(skip)


# ---------------------------------------------------------------------------
# httpx client policy — configurable timeout + bounded retry (P1)
# ---------------------------------------------------------------------------

_MAX_RETRIES = 3


def _test_timeout() -> httpx.Timeout:
    try:
        seconds = float(os.environ.get("LLMTIER_TEST_TIMEOUT", "30"))
    except ValueError:
        seconds = 30.0
    return httpx.Timeout(seconds, connect=min(5.0, seconds))


def _test_retries() -> int:
    try:
        value = int(os.environ.get("LLMTIER_TEST_RETRIES", "2"))
    except ValueError:
        value = 2
    return max(0, min(value, _MAX_RETRIES))


class _RetryTransport(httpx.HTTPTransport):
    """Retry transient connect/read/timeout failures, bounded to ≤3 attempts."""

    def __init__(self, retries: int = 0, **kwargs):
        super().__init__(**kwargs)
        self._retries = max(0, min(int(retries), _MAX_RETRIES))

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        attempt = 0
        while True:
            try:
                return super().handle_request(request)
            except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError):
                if attempt >= self._retries:
                    raise
                attempt += 1


def _make_client(base_url: str, token: str | None) -> httpx.Client:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return httpx.Client(
        base_url=base_url,
        headers=headers,
        timeout=_test_timeout(),
        transport=_RetryTransport(retries=_test_retries()),
    )


@pytest.fixture(scope="session")
def m5air_base_url() -> str:
    return M5AIR_BASE


@pytest.fixture(scope="session")
def api_client() -> httpx.Client:
    return _make_client(M5AIR_BASE, "dev-data")


@pytest.fixture(scope="session")
def admin_client() -> httpx.Client:
    return _make_client(M5AIR_BASE, "dev-admin")


@pytest.fixture(scope="session")
def bare_client() -> httpx.Client:
    """A credential-free client for the ``security:[]`` health endpoints.

    ST-HEALTH-001/02 require the 免鉴权 contract point to be *constructed*: the
    端点 is ``security:[]`` (openapi) and ``app._dispatch`` handles it before
    any ``_auth()`` call, so it must be reachable with **no** ``Authorization``
    header. ``api_client`` injects ``Bearer dev-data`` and therefore cannot
    falsify that claim (a route mistakenly moved behind auth would still 200
    with a valid token).
    """
    return httpx.Client(base_url=M5AIR_BASE, timeout=_test_timeout())


def is_retryable_error(response: httpx.Response) -> bool:
    """True when a non-2xx response is a *retryable* gateway error.

    The gateway marks transient upstream unavailability (503
    ``provider_unavailable`` / ``model_unavailable``) and admission back-pressure
    (429 ``rate_limit_exceeded``) with ``error.retryable == true``. A-class cases
    share one live m5air instance, so concurrent work can transiently trip these.
    Callers use this to retry the whole request a bounded number of times instead
    of failing on a genuinely external, non-deterministic condition.
    """
    if response.status_code < 400:
        return False
    try:
        body = response.json()
    except Exception:
        return False
    err = body.get("error") if isinstance(body, dict) else None
    return isinstance(err, dict) and err.get("retryable") is True


def request_with_retry(client: httpx.Client, method: str, path: str, *, attempts: int = 4,
                       backoff: float = 0.75, **kwargs) -> httpx.Response:
    """Send a request, retrying bounded on a retryable (5xx/429) gateway error.

    Retries only when the response is a retryable gateway error; any other
    outcome (2xx or a non-retryable error) is returned immediately so a genuine
    contract failure still fails fast. Returns the last response received.
    """
    resp = client.request(method, path, **kwargs)
    for attempt in range(1, max(1, attempts)):
        if not is_retryable_error(resp):
            return resp
        time.sleep(backoff * attempt)
        resp = client.request(method, path, **kwargs)
    return resp


def send_stream_with_retry(client: httpx.Client, method: str, path: str, *, attempts: int = 4,
                           backoff: float = 0.75, **kwargs) -> httpx.Response:
    """Open a streaming request, retrying bounded on a retryable status.

    Returns the first response whose status is not a retryable gateway error.
    Rejected responses are closed before retrying. The caller must close the
    returned response when done (``with resp:`` or ``resp.close()``).
    """
    request = client.build_request(method, path, **kwargs)
    resp = client.send(request, stream=True)
    for attempt in range(1, max(1, attempts)):
        if not is_retryable_error(resp):
            return resp
        resp.close()
        time.sleep(backoff * attempt)
        request = client.build_request(method, path, **kwargs)
        resp = client.send(request, stream=True)
    return resp


_TERMINAL_NAMES = ("response.completed", "response.incomplete", "response.failed")


def _collect_sse_with_done(resp: httpx.Response) -> tuple[list[tuple[str, dict]], bool]:
    """Parse SSE events AND retain the `data: [DONE]` sentinel flag."""
    events: list[tuple[str, dict]] = []
    event_name = None
    data_buf: list[str] = []
    saw_done = False
    for raw in resp.iter_lines():
        if raw is None:
            continue
        line = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
        if line.startswith("event:"):
            event_name = line[len("event:"):].strip()
        elif line.startswith("data:"):
            value = line[len("data:"):].strip()
            if value == "[DONE]":
                saw_done = True
            data_buf.append(value)
        elif line == "":
            if event_name and data_buf:
                payload_str = "\n".join(data_buf)
                try:
                    payload = json.loads(payload_str)
                except json.JSONDecodeError:
                    payload = {"_raw": payload_str}
                events.append((event_name, payload))
            event_name = None
            data_buf = []
    return events, saw_done


def post_stream_collect(client: httpx.Client, body: dict, *, attempts: int = 4,
                        backoff: float = 0.75) -> tuple[list[tuple[str, dict]], bool]:
    """POST a streaming request; return ``(events, saw_done)`` with retry.

    Retries the whole request on a retryable gateway error (shared-instance
    noise) and returns the first fully-parsed stream. Does not retry on
    truncation — callers needing a specific terminal use
    :func:`post_stream_until_terminal`.
    """
    last_status = None
    for attempt in range(1, max(1, attempts) + 1):
        resp = send_stream_with_retry(client, "POST", "/v1/responses", json=body,
                                      attempts=attempts, backoff=backoff)
        try:
            if resp.status_code != 200:
                last_status = resp.status_code
                time.sleep(backoff * attempt)
                continue
            return _collect_sse_with_done(resp)
        finally:
            resp.close()
    raise AssertionError(f"stream request kept failing with a retryable status (last={last_status})")


def post_stream_until_terminal(client: httpx.Client, body: dict, *, terminal: str = "response.completed",
                               attempts: int = 4, backoff: float = 0.75):
    """POST streaming; retry (bounded) until the unique terminal is ``terminal``.

    ``terminal`` is the full SSE event name (default ``"response.completed"``).
    Returns ``(events, saw_done, attempts_used)``. Retries on retryable status
    and on a truncation terminal (``response.incomplete``) when a completion
    terminal is required. A ``response.failed`` terminal is returned immediately
    (caller decides).
    """
    events, saw_done = [], False
    for attempt in range(1, max(1, attempts) + 1):
        events, saw_done = post_stream_collect(client, body, attempts=1, backoff=backoff)
        names = [n for n, _ in events]
        terminals = [n for n in names if n in _TERMINAL_NAMES]
        if terminals == [terminal] or (terminals and terminals[0] == "response.failed"):
            return events, saw_done, attempt
        time.sleep(backoff * attempt)
    return events, saw_done, max(1, attempts)


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

def _find_free_port(bind_ip: str = "127.0.0.1") -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((bind_ip, 0))
        return s.getsockname()[1]


def _detect_lan_ip() -> str | None:
    """Return this machine's RFC1918 LAN IP (TS-003), trying env override first."""
    override = os.environ.get("LLMTIER_TEST_LAN_IP")
    if override:
        return override
    probes = (os.environ.get("LLMTIER_LAN_PROBE_HOST"), "192.168.1.9", "192.168.1.1", "10.0.0.1")
    for host in probes:
        if not host:
            continue
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect((host, 8181))
                ip = s.getsockname()[0]
        except OSError:
            continue
        if ip and not ip.startswith("127."):
            return ip
    try:
        ip = socket.gethostbyname(socket.gethostname())
    except OSError:
        return None
    return ip if ip and not ip.startswith("127.") else None


class _FakeProvider:
    """A LAN-bound OpenAI-compatible fake upstream (TS-003 compliant)."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.url = f"http://{host}:{port}/v1"
        self.health_url = f"http://{host}:{port}/healthz"
        self._proc: subprocess.Popen | None = None

    def start(self) -> None:
        self._proc = subprocess.Popen(
            [PYTHON, str(FAKE_PROVIDER_SCRIPT), "--host", self.host, "--port", str(self.port)],
            cwd=str(REPO_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(40):
            if self._proc.poll() is not None:
                raise RuntimeError("fake provider exited during startup")
            try:
                with urllib.request.urlopen(self.health_url, timeout=1) as resp:
                    if resp.status == 200:
                        return
            except (urllib.error.URLError, OSError):
                pass
            time.sleep(0.25)
        self.stop()
        raise RuntimeError(f"fake provider did not become healthy at {self.health_url}")

    def stop(self) -> None:
        if self._proc is None:
            return
        self._proc.terminate()
        try:
            self._proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._proc.kill()
            self._proc.wait()
        self._proc = None

    def _control(self, path: str) -> None:
        try:
            with urllib.request.urlopen(f"http://{self.host}:{self.port}{path}", timeout=5):
                pass
        except (urllib.error.URLError, OSError):
            pass

    def release_slow(self) -> None:
        """Open the slow-embeddings gate so blocked requests drain immediately."""
        self._control("/control/release")

    def reset_slow(self) -> None:
        self._control("/control/reset")


@pytest.fixture(scope="session")
def fake_provider_b() -> Generator[_FakeProvider, None, None]:
    """The LAN-bound fake upstream for B-class cases (TS-003)."""
    override = os.environ.get("LLMTIER_TEST_PROVIDER_URL")
    if override:
        pytest.skip("LLMTIER_TEST_PROVIDER_URL set: fake provider control unavailable")
    lan_ip = _detect_lan_ip()
    if not lan_ip:
        pytest.skip("TS-003: no LAN IP available for the B-class upstream provider")
    provider = _FakeProvider(lan_ip, _find_free_port(lan_ip))
    provider.start()
    try:
        yield provider
    finally:
        provider.stop()


@pytest.fixture(scope="session")
def provider_endpoint_b(fake_provider_b: _FakeProvider) -> str:
    """LAN-IP upstream URL for the B-class baseline provider (TS-003)."""
    return fake_provider_b.url


class LLMTierInstance:
    """Manage a temporary LLMTier v0.3 process with an isolated SQLite DB."""

    def __init__(self, settings: dict | None = None, dev_mode: bool = True, extra_env: dict | None = None):
        self.port = _find_free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        self._tmpdir = Path(tempfile.mkdtemp(prefix="llmtier_b_"))
        self._db_path = self._tmpdir / "test.sqlite3"
        self._settings_path = self._tmpdir / "settings.json"
        self._settings = settings
        self._dev_mode = dev_mode
        self._extra_env = extra_env or {}

        if settings is not None:
            self._settings_path.write_text(json.dumps(settings))

        self._proc: subprocess.Popen | None = None
        self._spawn()

    def _spawn(self) -> None:
        """Start the LLMTier process on the existing db/settings (no health wait)."""
        # Start from a clean LLMTIER_* env so leaked tokens / DEV_MODE from the
        # parent pytest process cannot change auth behaviour (ST-AUTH-007 etc.).
        env = os.environ.copy()
        for key in [k for k in env if k.startswith("LLMTIER_")]:
            del env[key]
        if self._dev_mode:
            env["LLMTIER_DEV_MODE"] = "1"
            env["LLMTIER_ADMIN_TOKEN"] = "dev-admin"
            env["LLMTIER_DATA_TOKEN"] = "dev-data"
        # auth.py derives trusted-LAN access from the client address only
        # (loopback / RFC1918); it does not read LLMTIER_TRUSTED_LAN_MODE.
        # Keep the var set for parity with the deployed instance config.
        env["LLMTIER_TRUSTED_LAN_MODE"] = "1"
        env["LLMTIER_DATABASE"] = str(self._db_path)
        env["PYTHONPATH"] = str(SRC_ROOT)
        if self._settings is not None:
            env["LLMTIER_SETTINGS"] = str(self._settings_path)
        for key, value in self._extra_env.items():
            env[key] = str(value)

        self._proc = subprocess.Popen(
            [PYTHON, "-m", "http_api",
             "--host", "127.0.0.1",
             "--port", str(self.port)],
            env=env,
            cwd=str(REPO_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _terminate(self) -> None:
        if self._proc is None:
            return
        self._proc.terminate()
        try:
            self._proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._proc.kill()
            self._proc.wait()
        self._proc = None

    def kill(self) -> None:
        """Hard-kill the process (SIGKILL) without removing the db (T-MET-CRASH)."""
        if self._proc is None:
            return
        self._proc.kill()
        self._proc.wait()
        self._proc = None

    def restart(self) -> None:
        """Stop then start again on the SAME port/db/settings (crash-recovery)."""
        self._terminate()
        self._spawn()
        self.start()

    @property
    def db_path(self) -> Path:
        return self._db_path

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
        self._terminate()
        try:
            import shutil
            shutil.rmtree(self._tmpdir)
        except OSError:
            pass

    def admin_client(self) -> httpx.Client:
        return _make_client(self.base_url, "dev-admin")

    def api_client(self) -> httpx.Client:
        return _make_client(self.base_url, "dev-data")


def _baseline_settings(provider_endpoint: str) -> dict:
    return {
        "providers": [
            {
                "id": "prov_b",
                "name": "Baseline Provider B",
                "kind": "local",
                "endpoint": provider_endpoint,
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
            for tier in FIXED_TIERS
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


def _probe_deployment(inst: "LLMTierInstance", deployment_id: str) -> str:
    """Probe a deployment so its health becomes routable; return the status."""
    client = inst.admin_client()
    try:
        resp = client.post(
            "/v1/probes",
            json={"deployment_id": deployment_id, "confirm_external_call": True},
        )
        assert resp.status_code == 200, f"probe {deployment_id} failed: {resp.status_code}: {resp.text}"
        return resp.json().get("status", "")
    finally:
        client.close()


@pytest.fixture(scope="session")
def llmtier_b(provider_endpoint_b: str) -> Generator[LLMTierInstance, None, None]:
    inst = LLMTierInstance(_baseline_settings(provider_endpoint_b))
    inst.start()
    status = _probe_deployment(inst, "depl_b")
    assert status == "healthy", f"baseline depl_b probe not healthy: {status}"
    yield inst
    inst.stop()


@pytest.fixture(scope="session")
def llmtier_b_unprobed(provider_endpoint_b: str) -> Generator[LLMTierInstance, None, None]:
    """ST-HEALTH-003: a bootstrapped baseline instance whose ``depl_b`` is never probed.

    ``_baseline_settings`` seeds 1 provider / 1 deployment / 7 fixed tiers;
    ``deployments.health`` defaults to ``'unknown'`` (migration 001). Because
    ``_probe_deployment`` is **not** called, every tier has a candidate
    (``candidates()`` non-empty) but ``healthy == 0`` ⇒ ``readiness_view``
    yields ``degraded`` / HTTP 503. Must NOT reuse ``llmtier_b``: it probes
    ``depl_b`` to ``healthy`` at start ⇒ ``ready``. The instance is read-only
    against the health endpoint (no ``POST /v1/probes`` is ever issued).
    """
    inst = LLMTierInstance(_baseline_settings(provider_endpoint_b))
    inst.start()
    yield inst
    inst.stop()


def _embeddings_settings(provider_endpoint: str, backend_model: str) -> dict:
    """Baseline B settings with an embeddings-capable deployment.

    `Senior` (and every non-Embedding tier) also requires `responses`, so the
    deployment advertises both; `EmbeddingsService.create` additionally requires
    `embeddings is True` on the resolved service level.
    """
    settings = _baseline_settings(provider_endpoint)
    caps = settings["deployments"][0]["capabilities"]
    caps["embeddings"] = True
    settings["deployments"][0]["backend_model"] = backend_model
    return settings


def _embeddings_instance(endpoint: str, backend_model: str) -> LLMTierInstance:
    inst = LLMTierInstance(_embeddings_settings(endpoint, backend_model))
    inst.start()
    status = _probe_deployment(inst, "depl_b")
    assert status == "healthy", f"embeddings depl_b probe not healthy: {status}"
    return inst


def _tools_settings(provider_endpoint: str) -> dict:
    """Baseline B settings whose deployment advertises ``tools=True`` (ST-RESP-004).

    The fake provider deterministically echoes the tool name as a
    ``function_call`` when the prompt contains ``CALL_TOOL`` and ``tools`` is
    present (see ``tests/fixtures/models/v03_fake_provider.py``), which makes the
    "tools 透传" claim falsifiable.
    """
    settings = _baseline_settings(provider_endpoint)
    settings["deployments"][0]["capabilities"]["tools"] = True
    return settings


@pytest.fixture(scope="session")
def llmtier_b_tools(provider_endpoint_b: str) -> Generator[LLMTierInstance, None, None]:
    """ST-RESP-004: tools-capable B instance backed by the echoing fake provider."""
    inst = LLMTierInstance(_tools_settings(provider_endpoint_b))
    inst.start()
    status = _probe_deployment(inst, "depl_b")
    assert status == "healthy", f"tools depl_b probe not healthy: {status}"
    yield inst
    inst.stop()


@pytest.fixture(scope="session")
def llmtier_b_emb(provider_endpoint_b: str) -> Generator[LLMTierInstance, None, None]:
    """Embeddings baseline instance: the fake provider answers /v1/embeddings."""
    inst = _embeddings_instance(provider_endpoint_b, "test-model")
    yield inst
    inst.stop()


@pytest.fixture(scope="session")
def llmtier_b_emb_slow(provider_endpoint_b: str) -> Generator[LLMTierInstance, None, None]:
    """Embeddings instance whose upstream blocks, to saturate admission (ST-EMB-008)."""
    inst = _embeddings_instance(provider_endpoint_b, "slow-embeddings")
    yield inst
    inst.stop()


@pytest.fixture(scope="session")
def llmtier_b_emb_contract(provider_endpoint_b: str) -> Generator[LLMTierInstance, None, None]:
    """Embeddings instance whose upstream violates the payload contract (ST-EMB-009)."""
    inst = _embeddings_instance(provider_endpoint_b, "force-bad-contract")
    yield inst
    inst.stop()


@pytest.fixture(scope="session")
def llmtier_b_emb_503(provider_endpoint_b: str) -> Generator[LLMTierInstance, None, None]:
    """Embeddings instance whose upstream returns 503 (ST-EMB-010)."""
    inst = _embeddings_instance(provider_endpoint_b, "force-503")
    yield inst
    inst.stop()


def _instance_with_backend(endpoint: str, backend_model: str, probe: bool = True) -> LLMTierInstance:
    """Baseline B instance whose depl_b targets ``backend_model`` at ``endpoint``.

    ``probe=False`` leaves depl_b unrouted (health unknown) — used by cases that
    need to control health explicitly (e.g. ST-RESP-019).
    """
    settings = _baseline_settings(endpoint)
    settings["deployments"][0]["backend_model"] = backend_model
    inst = LLMTierInstance(settings)
    inst.start()
    if probe:
        status = _probe_deployment(inst, "depl_b")
        assert status == "healthy", f"depl_b probe not healthy: {status}"
    return inst


@pytest.fixture(scope="session")
def llmtier_b_unhealthy(provider_endpoint_b: str) -> Generator[LLMTierInstance, None, None]:
    """ST-RESP-019: depl_b points at an unreachable LAN endpoint, never probed healthily."""
    inst = _instance_with_backend("http://192.168.1.254:9/v1", "test-model", probe=False)
    yield inst
    inst.stop()


@pytest.fixture
def llmtier_b_resp_slow(provider_endpoint_b: str) -> Generator[LLMTierInstance, None, None]:
    """ST-RESP-020: dedicated instance whose upstream blocks on the fake provider gate.

    The sole admission slot is held deterministically by one in-flight request
    (backend_model ``slow-responses`` blocks in the fake provider until
    ``fake_provider_b.release_slow()``); teardown releases the gate so every
    queued request drains immediately (no leaked long sleep). Function-scoped
    for an isolated SQLite/port.
    """
    inst = _instance_with_backend(provider_endpoint_b, "slow-responses", probe=True)
    yield inst
    inst.stop()


@pytest.fixture
def llmtier_b_diag(provider_endpoint_b: str) -> Generator[LLMTierInstance, None, None]:
    """Dedicated baseline instance for mutation cases (ST-RESP-020/21/22/24).

    Function-scoped so each case gets an isolated SQLite/port and its injection
    or provider edits never leak into the session-scoped ``llmtier_b``.
    """
    inst = _instance_with_backend(provider_endpoint_b, "test-model", probe=True)
    yield inst
    inst.stop()


@pytest.fixture(scope="session")
def llmtier_b_http_stub(provider_endpoint_b: str) -> Generator[LLMTierInstance, None, None]:
    """ST-RESP-023: depl_b whose upstream returns configured non-success HTTP codes."""
    inst = _instance_with_backend(provider_endpoint_b, "force-http-422", probe=True)
    yield inst
    inst.stop()


@pytest.fixture(scope="session")
def llmtier_b_contract_stub(provider_endpoint_b: str) -> Generator[LLMTierInstance, None, None]:
    """ST-RESP-025: depl_b whose upstream emits contract-violating Responses SSE.

    The backend_model is reconfigured per sub-test via the admin API; the initial
    value only has to be a healthy model (probe hits /v1/models).
    """
    inst = _instance_with_backend(provider_endpoint_b, "test-model", probe=True)
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


@pytest.fixture(scope="session")
def llmtier_b_no_bootstrap() -> Generator[LLMTierInstance, None, None]:
    """ST-HEALTH-005 arm (a): an empty store started WITHOUT a settings path.

    ``LLMTierInstance(settings=None)`` never writes ``LLMTIER_SETTINGS``, so the
    fresh SQLite store has no ``bootstrap_sha256`` and
    ``registry.bootstrap_settings(None)`` raises ``ApiError(503,
    "bootstrap_required")`` — captured into ``app.bootstrap_error``. The process
    still serves ``/healthz`` (200) while ``/readyz`` short-circuits to 503
    ``{"status":"not_ready","models":[]}``. Must NOT be reused for ST-HEALTH-004
    (bootstrap succeeds there); the fixture is read-only and never contacts an
    upstream (TS-003 not applicable).
    """
    inst = LLMTierInstance(settings=None)
    inst.start()
    yield inst
    inst.stop()


# ---------------------------------------------------------------------------
# B-class store-unavailability helpers (OBS-STATS/SNAP/TRACE-03, ST-OBSDEPL-005)
# ---------------------------------------------------------------------------

class StoreTriplet:
    """Make a live SQLite store unavailable by replacing the db path with a dir.

    Mirrors the ST-USAGE-008 technique: move ``<db>``/``<db>-wal``/``<db>-shm``
    aside and drop an empty *directory* at the db path so every new
    ``sqlite3.connect(<db>)`` fails (the implementation opens a per-request
    connection and closes it in ``_run``). ``restore()`` is idempotent and
    atomic enough for tests; always call it in a ``finally``.
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self._stash = self.db_path.with_name(self.db_path.name + ".stash")
        self._moved: list[tuple[Path, Path]] = []
        self._placeholder: Path | None = None

    def break_store(self) -> None:
        self._stash.mkdir(parents=True, exist_ok=True)
        for suffix in ("", "-wal", "-shm"):
            src = Path(str(self.db_path) + suffix)
            if src.exists():
                dst = self._stash / (src.name)
                os.replace(src, dst)
                self._moved.append((dst, src))
        # Drop a directory in place of the db file so sqlite3.connect() fails.
        self._placeholder = self.db_path
        self._placeholder.mkdir()

    def restore(self) -> None:
        if self._placeholder is not None and self._placeholder.is_dir():
            self._placeholder.rmdir()
            self._placeholder = None
        for dst, src in self._moved:
            if dst.exists():
                os.replace(dst, src)
        self._moved = []


@pytest.fixture
def store_triplet() -> StoreTriplet:
    """Factory fixture: ``store_triplet(db_path)`` → StoreTriplet breaker."""
    return StoreTriplet


def _dedicated_diag_instance(provider_endpoint: str) -> LLMTierInstance:
    """A fresh, isolated live instance for store-unavailability cases."""
    inst = LLMTierInstance(_baseline_settings(provider_endpoint))
    inst.start()
    status = _probe_deployment(inst, "depl_b")
    assert status == "healthy", f"diag-store depl_b probe not healthy: {status}"
    return inst


@pytest.fixture
def llmtier_b_diag_store(provider_endpoint_b: str) -> Generator[LLMTierInstance, None, None]:
    """Dedicated LLMTierInstance (own tmp SQLite/port) for OBS store-503 cases.

    Function-scoped on purpose: the case moves this instance's db triplet, so it
    must never be the session-scoped ``llmtier_b`` (whose db is shared).
    """
    inst = _dedicated_diag_instance(provider_endpoint_b)
    yield inst
    inst.stop()


# ---------------------------------------------------------------------------
# B-class restart fixture — ledger crash/restart recovery (ST-USAGE-009)
# ---------------------------------------------------------------------------

@pytest.fixture
def llmtier_b_restart(provider_endpoint_b: str) -> Generator[LLMTierInstance, None, None]:
    """Dedicated baseline instance exposing ``restart()``/``kill()`` (T-MET-CRASH).

    Starts WITHOUT probing ``depl_b`` so ST-USAGE-009 path A can create an orphan
    unknown obligation via a 503 ``model_unavailable`` admission rejection.
    """
    inst = LLMTierInstance(_baseline_settings(provider_endpoint_b))
    inst.start()
    yield inst
    inst.stop()


@pytest.fixture
def llmtier_b_crash(provider_endpoint_b: str) -> Generator[LLMTierInstance, None, None]:
    """Dedicated instance for ST-USAGE-009 path B (real in-flight crash).

    ``depl_b`` IS probed ``healthy`` (so a Responses request is admitted and
    enters the adapter), and ``LLMTIER_SLOW_ADAPTER_DELAY`` keeps the request
    in-flight inside ``SlowAdapter.complete`` long enough for the test to
    SIGKILL the process with a committed obligation and no ``finish``.
    """
    settings = _baseline_settings(provider_endpoint_b)
    inst = LLMTierInstance(settings, extra_env={"LLMTIER_SLOW_ADAPTER_DELAY": "30"})
    inst.start()
    status = _probe_deployment(inst, "depl_b")
    assert status == "healthy", f"crash-path depl_b probe not healthy: {status}"
    yield inst
    inst.stop()


@pytest.fixture
def llmtier_b_ratelimit(provider_endpoint_b: str) -> Generator[LLMTierInstance, None, None]:
    """ST-RATELIMIT-001: provider max_concurrent_requests=1 + slow adapter.

    ``LLMTIER_SLOW_ADAPTER_DELAY=1.0`` replaces the real upstream adapter with
    an in-process ``SlowAdapter`` (no network call), so the single provider
    concurrency slot is held ~1 s per request and 6 concurrent requests must
    drain through the 32-deep queue without a 429. ``depl_b`` health is set
    directly (never probed over the network — the adapter is replaced), keeping
    the case hermetic on the B-class temporary instance.

    TS-002 依赖：
      Endpoint: 临时 LLMTier 实例（llmtier_b_ratelimit），127.0.0.1:<临时端口>
      上游: 无网络调用（SlowAdapter 进程内替身）；
            provider_usage_profiles.max_concurrent_requests=1
      Auth: Bearer dev-data
    """
    import sqlite3

    settings = _baseline_settings(provider_endpoint_b)
    inst = LLMTierInstance(settings, extra_env={"LLMTIER_SLOW_ADAPTER_DELAY": "1.0"})
    inst.start()
    with sqlite3.connect(str(inst.db_path)) as con:
        con.execute("UPDATE deployments SET health='healthy' WHERE id='depl_b'")
        con.execute(
            "UPDATE provider_usage_profiles SET max_concurrent_requests=1 "
            "WHERE provider_id='prov_b'"
        )
        con.commit()
    yield inst
    inst.stop()


def error_envelope(response) -> dict:
    """Return the ``error`` object from a typed error response (asserts shape)."""
    body = response.json()
    assert set(body.keys()) == {"error"}, f"envelope must have exactly one 'error' key: {body}"
    err = body["error"]
    assert set(err.keys()) == {"message", "type", "code", "param", "retryable"}, (
        f"error envelope must have exactly 5 keys: {sorted(err.keys())}"
    )
    return err


def version_conflict_envelope(response) -> dict:
    """Return the ``error`` object of a 412 ``version_conflict`` (5 keys + ``current_version``)."""
    body = response.json()
    assert set(body.keys()) == {"error"}, f"envelope must have exactly one 'error' key: {body}"
    err = body["error"]
    assert set(err.keys()) == {"message", "type", "code", "param", "retryable", "current_version"}, (
        f"412 envelope must be the 5 required keys plus 'current_version': {sorted(err.keys())}"
    )
    return err


# ---------------------------------------------------------------------------
# UI (ST-UI-001..010) fixtures — real headless Chrome over CDP (RISK-UI-EXEC-1)
# ---------------------------------------------------------------------------

from tests.common.drivers import ui_support  # noqa: E402


@pytest.fixture(scope="session")
def ui_browser() -> str:
    ok, detail = ui_support.browser_available()
    if not ok:
        pytest.skip(f"UI browser unavailable ({detail}); set LLMTIER_BROWSER")
    return detail


@pytest.fixture(scope="session")
def ui_node() -> str:
    node = ui_support.node_binary()
    if not ui_support.which(node):
        pytest.skip(f"node unavailable ({node}); set LLMTIER_NODE")
    return node


@pytest.fixture(scope="session")
def ui_instance(provider_endpoint_b: str) -> Generator[LLMTierInstance, None, None]:
    """A hermetic baseline LLMTier instance (1 provider, 1 deployment, 7 tiers).

    Serves both the API and the static UI on the same loopback origin.
    """
    inst = LLMTierInstance(_baseline_settings(provider_endpoint_b))
    inst.start()
    status = _probe_deployment(inst, "depl_b")
    assert status == "healthy", f"UI baseline depl_b probe not healthy: {status}"
    yield inst
    inst.stop()


def baseline_settings(provider_endpoint: str) -> dict:
    """The canonical B-class baseline settings (1 provider/deployment/7 tiers)."""
    return _baseline_settings(provider_endpoint)


run_scenario = ui_support.run_scenario
artifact_dir = ui_support.artifact_dir
assert_ui_evidence = ui_support.assert_evidence
