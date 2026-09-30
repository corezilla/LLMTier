#!/usr/bin/env python3
"""Standalone environment readiness check (system test plan §3 Go/No-Go).

Reproduces the six A-class checks that `tests/system/api_test_v03/conftest.py`
runs in `pytest_configure`, plus the B-class preconditions (a temporary
`LLMTierInstance` can start and answer ``/healthz`` 200, and a fake upstream is
reachable on a LAN IP per `testing-standard.md` TS-003).

A-class checks (§2.1.1–§2.1.6):
  1. m5air `/healthz` 200 + ``status=ok`` + ``version`` is a string
  2. m5air `/readyz` 200 + exactly the 7 fixed tiers
  3. m5air OMLX `192.168.1.9:9000` `/models` 200
  4. m5mac OMLX `192.168.1.8:9000` `/models` 200
  5. `provider_omlx_m5mac.secret_ref` is a ``file:`` path and ``has_secret=true``
  6. required A providers/deployments are registered

B-class preconditions:
  B1. a temporary `LLMTierInstance` boots and `/healthz` returns 200
  B2. a fake upstream is reachable on a LAN IP (RFC1918), TS-003 compliant

Output: human table by default, ``--json`` for a machine-readable report.
Exit codes: 0 = all pass, 2 = any check failed.

This mirrors `tools/test_report.py` style: argparse, deterministic,
stdlib-only.

Usage::

    tools/check_env.py --class a
    tools/check_env.py --class all --json
    tools/check_env.py --base-url http://192.168.1.9:8181 \
        --admin-token dev-admin --data-token dev-data
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
FAKE_PROVIDER_SCRIPT = REPO_ROOT / "tests" / "fixtures" / "v03_fake_provider.py"

DEFAULT_BASE_URL = "http://192.168.1.9:8181"
DEFAULT_ADMIN_TOKEN = "dev-admin"
DEFAULT_DATA_TOKEN = "dev-data"
M5AIR_OMLX = "http://192.168.1.9:9000/v1"
M5MAC_OMLX = "http://192.168.1.8:9000/v1"
OMLX_TOKEN = "9832"

FIXED_TIERS = ("Senior", "Junior", "Worker", "Associate", "Engineer", "Executor", "Embedding-v1")
REQUIRED_A_PROVIDERS = ("provider_local", "provider_minimax", "provider_omlx_m5mac")
REQUIRED_A_DEPLOYMENTS = ("dep_local_gemma", "dep_local_bge_m3", "dep_omlx_qwen36", "dep_minimax_m27")

PYTHON = os.environ.get("LLMTIER_TEST_PYTHON", sys.executable)

EXIT_OK = 0
EXIT_FAIL = 2


@dataclass
class CheckResult:
    id: str
    label: str
    ok: bool
    detail: str


@dataclass
class EnvConfig:
    base_url: str = DEFAULT_BASE_URL
    admin_token: str = DEFAULT_ADMIN_TOKEN
    data_token: str = DEFAULT_DATA_TOKEN
    m5air_omlx: str = M5AIR_OMLX
    m5mac_omlx: str = M5MAC_OMLX
    lan_ip_override: str | None = None
    timeout: float = 5.0
    python: str = PYTHON
    repo_root: Path = REPO_ROOT
    src_root: Path = SRC_ROOT
    fake_provider_script: Path = FAKE_PROVIDER_SCRIPT


# ---------------------------------------------------------------------------
# HTTP helpers (stdlib only)
# ---------------------------------------------------------------------------

def http_get(url: str, headers: dict | None = None, timeout: float = 5.0) -> tuple[int, str]:
    """Return ``(status, body)``; network failures surface as status 0."""
    try:
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001 - any failure is a check failure
        return 0, f"{type(exc).__name__}: {exc}"


def _admin_headers(cfg: EnvConfig) -> dict:
    return {"Authorization": f"Bearer {cfg.admin_token}"}


# ---------------------------------------------------------------------------
# A-class checks — pure functions over cfg, return CheckResult
# ---------------------------------------------------------------------------

def check_healthz(cfg: EnvConfig) -> CheckResult:
    status, body = http_get(f"{cfg.base_url}/healthz", timeout=cfg.timeout)
    label = "§2.1.1 m5air LLMTier /healthz 200 + status=ok + version:str"
    if status != 200:
        return CheckResult("A1", label, False, f"/healthz returned {status}: {body[:120]}")
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        return CheckResult("A1", label, False, f"/healthz body not JSON: {exc}")
    if data.get("status") != "ok":
        return CheckResult("A1", label, False, f"/healthz status field != 'ok': {data}")
    if not isinstance(data.get("version"), str):
        return CheckResult("A1", label, False, f"/healthz version field not a string: {data}")
    return CheckResult("A1", label, True, f"ok (version={data.get('version')!r})")


def check_readyz(cfg: EnvConfig) -> CheckResult:
    status, body = http_get(f"{cfg.base_url}/readyz", timeout=cfg.timeout)
    label = "§2.1.2 m5air LLMTier /readyz 200 + exactly 7 fixed tiers"
    if status != 200:
        return CheckResult("A2", label, False, f"/readyz returned {status}: {body[:120]}")
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        return CheckResult("A2", label, False, f"/readyz body not JSON: {exc}")
    models = data.get("models") or data.get("tiers") or []
    ids = {m.get("id") if isinstance(m, dict) else m for m in models}
    missing = set(FIXED_TIERS) - ids
    if missing:
        return CheckResult("A2", label, False, f"/readyz missing tiers: {sorted(missing)}")
    extra = ids - set(FIXED_TIERS)
    if extra:
        return CheckResult("A2", label, False, f"/readyz has non-fixed tiers: {sorted(extra)}")
    return CheckResult("A2", label, True, f"ok ({len(models)} models, 7 fixed tiers)")


def check_omlx(url: str, name: str, cfg: EnvConfig) -> CheckResult:
    status, body = http_get(f"{url}/models", {"Authorization": f"Bearer {OMLX_TOKEN}"}, timeout=cfg.timeout)
    label = f"§2.1.{3 if name == 'm5air' else 4} {name} OMLX 9000 健康"
    if status != 200:
        return CheckResult("A3" if name == "m5air" else "A4", label, False,
                           f"{name} OMLX /models returned {status}: {body[:120]}")
    return CheckResult("A3" if name == "m5air" else "A4", label, True, "ok")


def check_provider_omlx_m5mac_secret_ref(cfg: EnvConfig) -> CheckResult:
    label = "§2.1.5 provider_omlx_m5mac.secret_ref = file: 且 has_secret=true"
    status, body = http_get(f"{cfg.base_url}/v1/providers/provider_omlx_m5mac",
                            _admin_headers(cfg), timeout=cfg.timeout)
    if status != 200:
        return CheckResult("A5", label, False, f"/providers/provider_omlx_m5mac returned {status}")
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        return CheckResult("A5", label, False, f"body not JSON: {exc}")
    if not str(data.get("secret_ref") or "").startswith("file:"):
        return CheckResult("A5", label, False,
                           f"secret_ref not a file: reference: {data.get('secret_ref')!r}")
    if not data.get("has_secret"):
        return CheckResult("A5", label, False, "provider_omlx_m5mac.has_secret=False (expect True)")
    return CheckResult("A5", label, True, "ok (secret_ref=file:, has_secret=true)")


def check_required_a_resources(cfg: EnvConfig) -> CheckResult:
    label = "§2.1.6 必需 provider/deployment 已注册"
    headers = _admin_headers(cfg)
    for pid in REQUIRED_A_PROVIDERS:
        status, _ = http_get(f"{cfg.base_url}/v1/providers/{pid}", headers, timeout=cfg.timeout)
        if status != 200:
            return CheckResult("A6", label, False, f"provider {pid} missing (HTTP {status})")
    for did in REQUIRED_A_DEPLOYMENTS:
        status, _ = http_get(f"{cfg.base_url}/v1/deployments/{did}", headers, timeout=cfg.timeout)
        if status != 200:
            return CheckResult("A6", label, False, f"deployment {did} missing (HTTP {status})")
    return CheckResult("A6", label, True,
                       f"ok ({len(REQUIRED_A_PROVIDERS)} providers, {len(REQUIRED_A_DEPLOYMENTS)} deployments)")


A_CHECKS = (
    check_healthz,
    check_readyz,
    lambda cfg: check_omlx(cfg.m5air_omlx, "m5air", cfg),
    lambda cfg: check_omlx(cfg.m5mac_omlx, "m5mac", cfg),
    check_provider_omlx_m5mac_secret_ref,
    check_required_a_resources,
)


# ---------------------------------------------------------------------------
# B-class preconditions
# ---------------------------------------------------------------------------

def detect_lan_ip(override: str | None = None, timeout: float = 5.0) -> str | None:
    """Return an RFC1918 LAN IP (TS-003), env override first, else None."""
    if override:
        return override
    env_override = os.environ.get("LLMTIER_TEST_LAN_IP")
    if env_override:
        return env_override
    probes = (os.environ.get("LLMTIER_LAN_PROBE_HOST"), "192.168.1.9", "192.168.1.1", "10.0.0.1")
    for host in probes:
        if not host:
            continue
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect((host, 8181))
                ip = sock.getsockname()[0]
        except OSError:
            continue
        if ip and not ip.startswith("127."):
            return ip
    try:
        ip = socket.gethostbyname(socket.gethostname())
    except OSError:
        return None
    return ip if ip and not ip.startswith("127.") else None


def _find_free_port(bind_ip: str) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((bind_ip, 0))
        return sock.getsockname()[1]


def check_fake_provider_lan(cfg: EnvConfig) -> CheckResult:
    label = "§2.1.B2 假上游可在 LAN IP 上启动并可探活 (TS-003)"
    script = cfg.fake_provider_script
    if not script.is_file():
        return CheckResult("B2", label, False, f"fake provider script missing: {script}")
    lan_ip = detect_lan_ip(cfg.lan_ip_override, cfg.timeout)
    if not lan_ip:
        return CheckResult("B2", label, False,
                           "no RFC1918 LAN IP (TS-003); set LLMTIER_TEST_LAN_IP or join a LAN")
    port = _find_free_port(lan_ip)
    proc = subprocess.Popen(
        [cfg.python, str(script), "--host", lan_ip, "--port", str(port)],
        cwd=str(cfg.repo_root), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(40):
            if proc.poll() is not None:
                return CheckResult("B2", label, False, "fake provider exited during startup")
            status, _ = http_get(f"http://{lan_ip}:{port}/healthz", timeout=1.0)
            if status == 200:
                return CheckResult("B2", label, True, f"ok (fake upstream at {lan_ip}:{port})")
            time.sleep(0.25)
        return CheckResult("B2", label, False, f"fake provider not healthy at {lan_ip}:{port}")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def check_temp_instance(cfg: EnvConfig) -> CheckResult:
    """Start a throwaway LLMTierInstance and confirm /healthz 200 (B1)."""
    label = "§2.1.B1 临时 LLMTierInstance 可启动且 /healthz 200"
    tmpdir = Path(tempfile.mkdtemp(prefix="llmtier_check_env_"))
    db_path = tmpdir / "check.sqlite3"
    port = _find_free_port("127.0.0.1")
    env = os.environ.copy()
    for key in [k for k in env if k.startswith("LLMTIER_")]:
        del env[key]
    env["LLMTIER_DEV_MODE"] = "1"
    env["LLMTIER_ADMIN_TOKEN"] = cfg.admin_token
    env["LLMTIER_DATA_TOKEN"] = cfg.data_token
    env["LLMTIER_TRUSTED_LAN_MODE"] = "1"
    env["LLMTIER_DATABASE"] = str(db_path)
    env["PYTHONPATH"] = str(cfg.src_root)
    proc = subprocess.Popen(
        [cfg.python, "-m", "http_api", "--host", "127.0.0.1", "--port", str(port)],
        env=env, cwd=str(cfg.repo_root), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(40):
            if proc.poll() is not None:
                return CheckResult("B1", label, False, "temp instance exited during startup")
            status, _ = http_get(f"{base}/healthz", timeout=2.0)
            if status == 200:
                return CheckResult("B1", label, True, f"ok (temp instance /healthz 200 on port {port})")
            time.sleep(0.25)
        return CheckResult("B1", label, False, f"temp instance not healthy on port {port}")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


B_CHECKS = (
    check_temp_instance,
    check_fake_provider_lan,
)


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def run_checks(kind: str, cfg: EnvConfig) -> list[CheckResult]:
    results: list[CheckResult] = []
    if kind in ("a", "all"):
        for check in A_CHECKS:
            try:
                results.append(check(cfg))
            except Exception as exc:  # noqa: BLE001 - never let a check crash the report
                results.append(CheckResult("A?", check.__name__, False, f"{type(exc).__name__}: {exc}"))
    if kind in ("b", "all"):
        for check in B_CHECKS:
            try:
                results.append(check(cfg))
            except Exception as exc:  # noqa: BLE001
                results.append(CheckResult("B?", check.__name__, False, f"{type(exc).__name__}: {exc}"))
    return results


def summarize(results: list[CheckResult]) -> dict:
    passed = sum(1 for r in results if r.ok)
    failed = [r for r in results if not r.ok]
    return {
        "schema_version": 1,
        "total": len(results),
        "passed": passed,
        "failed": len(failed),
        "all_pass": not failed,
        "checks": [
            {"id": r.id, "label": r.label, "ok": r.ok, "detail": r.detail}
            for r in results
        ],
    }


def render_table(report: dict) -> str:
    lines = ["LLMTier environment readiness check", "=" * 60]
    for check in report["checks"]:
        mark = "OK  " if check["ok"] else "FAIL"
        lines.append(f"[{mark}] {check['id']:>3}  {check['label']}")
        lines.append(f"        {check['detail']}")
    lines.append("-" * 60)
    lines.append(f"{report['passed']}/{report['total']} passed"
                 + ("" if report["all_pass"] else f"; {report['failed']} FAILED"))
    return "\n".join(lines)


def build_config(args: argparse.Namespace) -> EnvConfig:
    return EnvConfig(
        base_url=args.base_url,
        admin_token=args.admin_token,
        data_token=args.data_token,
        m5air_omlx=args.m5air_omlx,
        m5mac_omlx=args.m5mac_omlx,
        lan_ip_override=args.lan_ip,
        timeout=args.timeout,
        python=args.python,
        repo_root=args.repo_root,
        src_root=args.repo_root / "src",
        fake_provider_script=args.repo_root / "tests" / "fixtures" / "v03_fake_provider.py",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--class", dest="kind", choices=("a", "b", "all"), default="all",
                        help="which readiness class to check (default: all)")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL,
                        help=f"m5air LLMTier base URL (default: {DEFAULT_BASE_URL})")
    parser.add_argument("--admin-token", default=DEFAULT_ADMIN_TOKEN,
                        help="admin bearer token (default: dev-admin)")
    parser.add_argument("--data-token", default=DEFAULT_DATA_TOKEN,
                        help="data bearer token (default: dev-data)")
    parser.add_argument("--m5air-omlx", default=M5AIR_OMLX, help="m5air OMLX base URL")
    parser.add_argument("--m5mac-omlx", default=M5MAC_OMLX, help="m5mac OMLX base URL")
    parser.add_argument("--lan-ip", default=None, help="override LAN IP for the B-class fake upstream")
    parser.add_argument("--timeout", type=float, default=5.0, help="per-request timeout seconds")
    parser.add_argument("--python", default=PYTHON, help="Python interpreter for temp instances")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT, help="repository root")
    parser.add_argument("--json", action="store_true", help="emit a JSON report instead of a table")
    args = parser.parse_args(argv)

    cfg = build_config(args)
    results = run_checks(args.kind, cfg)
    report = summarize(results)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_table(report))
    return EXIT_OK if report["all_pass"] else EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
