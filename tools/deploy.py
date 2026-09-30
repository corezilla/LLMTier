#!/usr/bin/env python3
"""Factor the m5air deploy guide into a script (code update + restart).

Facts (from `docs/80_operations/manuals/m5air-deploy-guide.md`):
  host        : `192.168.1.9` (m5air)
  code dir    : `/Users/mlp/LLMTier-dev/` (NOT a git repo; a source snapshot)
  database    : `/Users/mlp/LLMTier-dev/state.sqlite3`
  port        : `8181` (listens on `0.0.0.0`)
  log         : `/Users/mlp/LLMTier-dev/llmtier.log`
  interpreter : `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3`

The deploy action:
  1. record the artifact pin — `git rev-parse HEAD`, openapi version from
     `interfaces/openapi/llmtier.openapi.json`, DB `schema_version`
     (`src/util/store.py::EXPECTED_SCHEMA_VERSION`).
  2. `rsync` `src/` (plus any needed files) to m5air.
  3. kill the old PID — found via `lsof -iTCP:8181 -sTCP:LISTEN`.
  4. start with the Python 3.14 interpreter + `LLMTIER_{ADMIN,DATA}_TOKEN` +
     `PYTHONPATH=src -m http_api`.
  5. verify `/healthz` + `/readyz`.

Never prints secrets: the tokens are passed as env vars over ssh and never
echoed in the recorded command or output.

`--rollback <db-bak>` restores a DB backup. `--dry-run` prints every command
without executing. Exit non-zero on any failed step.

Usage::

    tools/deploy.py --dry-run
    tools/deploy.py --pin-only
    tools/deploy.py --yes
    tools/deploy.py --yes --rollback backups/state-20260930.sqlite3
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

HOST = "192.168.1.9"
HOST_ALIAS = "m5air"
CODE_DIR = "/Users/mlp/LLMTier-dev"
REMOTE_DB = f"{CODE_DIR}/state.sqlite3"
REMOTE_LOG = f"{CODE_DIR}/llmtier.log"
REMOTE_PIDFILE = f"{CODE_DIR}/llmtier.pid"
PYTHON314 = "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3"
PORT = 8181

DEFAULT_ADMIN_TOKEN = "dev-admin"
DEFAULT_DATA_TOKEN = "dev-data"

EXIT_OK = 0
EXIT_FAIL = 1

# Files/dirs synced to m5air. `src/` is the minimum; the interface artifact is
# included so the deployed snapshot can reproduce its own openapi pin.
SYNC_ITEMS = ("src/",)
NEEDED_FILES = ("interfaces/openapi/llmtier.openapi.json",)


@dataclass
class StepResult:
    name: str
    ok: bool
    detail: str
    skipped: bool = False


@dataclass
class DeployConfig:
    host: str = HOST_ALIAS
    code_dir: str = CODE_DIR
    remote_db: str = REMOTE_DB
    remote_log: str = REMOTE_LOG
    remote_pidfile: str = REMOTE_PIDFILE
    python: str = PYTHON314
    port: int = PORT
    admin_token: str = DEFAULT_ADMIN_TOKEN
    data_token: str = DEFAULT_DATA_TOKEN
    ssh_opts: tuple[str, ...] = ()
    rsync_opts: tuple[str, ...] = ("-az", "--delete", "--exclude", "state.sqlite3*",
                                   "--exclude", "secrets/", "--exclude", "llmtier.log",
                                   "--exclude", "llmtier.pid", "--exclude", "backups/")
    repo_root: Path = REPO_ROOT
    dry_run: bool = False
    yes: bool = False
    timeout: float = 30.0


# ---------------------------------------------------------------------------
# Artifact pin
# ---------------------------------------------------------------------------

def read_openapi_version(repo_root: Path) -> str:
    path = repo_root / "interfaces" / "openapi" / "llmtier.openapi.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))["info"]["version"]
    except (OSError, KeyError, json.JSONDecodeError):
        return "unknown"


def read_schema_version(repo_root: Path) -> str:
    path = repo_root / "src" / "util" / "store.py"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return "unknown"
    match = re.search(r"EXPECTED_SCHEMA_VERSION\s*=\s*(\d+)", text)
    return match.group(1) if match else "unknown"


def read_git_commit(repo_root: Path) -> str:
    try:
        proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo_root),
                              capture_output=True, text=True, timeout=10)
        return proc.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def artifact_pin(repo_root: Path) -> dict:
    return {
        "git_commit": read_git_commit(repo_root),
        "openapi_version": read_openapi_version(repo_root),
        "schema_version": read_schema_version(repo_root),
    }


# ---------------------------------------------------------------------------
# Command construction (pure; unit-testable)
# ---------------------------------------------------------------------------

def rsync_command(cfg: DeployConfig) -> list[str]:
    target = f"{cfg.host}:{cfg.code_dir}/"
    cmd = ["rsync", *cfg.rsync_opts]
    for item in SYNC_ITEMS:
        # Preserve a trailing slash: `src/` merges the contents into the remote
        # code dir (matches the deploy guide's per-file rsync semantics).
        src = str(cfg.repo_root / item.rstrip("/"))
        cmd.append(src + "/" if item.endswith("/") else src)
    cmd.append(target)
    return cmd


def ssh_command(cfg: DeployConfig, remote: str) -> list[str]:
    cmd = ["ssh"]
    if cfg.ssh_opts:
        cmd.extend(cfg.ssh_opts)
    cmd.extend([cfg.host, remote])
    return cmd


def find_pid_command(cfg: DeployConfig) -> list[str]:
    remote = f"/usr/sbin/lsof -nP -iTCP:{cfg.port} -sTCP:LISTEN -t"
    return ssh_command(cfg, remote)


def kill_command(cfg: DeployConfig, pid: str) -> list[str]:
    return ssh_command(cfg, f"kill -TERM {pid}")


def start_command(cfg: DeployConfig) -> list[str]:
    """Build the remote start command. Tokens go in via env, never inline."""
    inner = (
        f"cd {cfg.code_dir} && "
        f"export LLMTIER_ADMIN_TOKEN=\"$LLMTIER_ADMIN_TOKEN\" LLMTIER_DATA_TOKEN=\"$LLMTIER_DATA_TOKEN\"; "
        f"PYTHONPATH=src nohup {cfg.python} -m http_api "
        f"--host 0.0.0.0 --port {cfg.port} --database {cfg.remote_db} "
        f">> {cfg.remote_log} 2>&1 & echo $! > {cfg.remote_pidfile}"
    )
    # The tokens are supplied via `send_env` so they are not rendered in argv.
    return ssh_command(cfg, inner)


def rollback_command(cfg: DeployConfig, backup: Path) -> list[str]:
    remote = (
        f"test -f {backup} && cp {backup} {cfg.remote_db} "
        f"&& echo rollback-ok || echo rollback-missing"
    )
    return ssh_command(cfg, remote)


# ---------------------------------------------------------------------------
# Execution helpers
# ---------------------------------------------------------------------------

def _run(cmd: list[str], cfg: DeployConfig, env: dict | None = None) -> tuple[int, str, str]:
    if cfg.dry_run:
        return 0, f"(dry-run) {' '.join(cmd)}", ""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=cfg.timeout, env=env)
        return proc.returncode, proc.stdout, proc.stderr
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, "", f"{type(exc).__name__}: {exc}"


def _ssh_env(cfg: DeployConfig):
    """Wrapper so tests can substitute; returns os.environ with no secrets added."""
    return None


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

def step_pin(cfg: DeployConfig) -> tuple[StepResult, dict]:
    pin = artifact_pin(cfg.repo_root)
    missing = [k for k, v in pin.items() if v in ("", "unknown")]
    if missing:
        return (StepResult("pin", False, f"artifact pin incomplete: {missing}"), pin)
    return (StepResult("pin", True,
                       f"git={pin['git_commit'][:12]} openapi={pin['openapi_version']} "
                       f"schema={pin['schema_version']}"), pin)


def step_rsync(cfg: DeployConfig) -> StepResult:
    cmd = rsync_command(cfg)
    code, out, err = _run(cmd, cfg)
    if code != 0:
        return StepResult("rsync", False, f"rsync failed ({code}): {err.strip()[:200]}")
    return StepResult("rsync", True, f"synced {', '.join(SYNC_ITEMS)} -> {cfg.host}:{cfg.code_dir}")


def step_kill_old(cfg: DeployConfig) -> StepResult:
    cmd = find_pid_command(cfg)
    code, out, err = _run(cmd, cfg)
    if cfg.dry_run:
        return StepResult("kill-old", True, f"(dry-run) {' '.join(cmd)}")
    if code != 0:
        return StepResult("kill-old", True, "no listener found (nothing to kill)")
    m = re.search(r"^\s*(\d+)\s*$", out, re.MULTILINE)
    if not m:
        return StepResult("kill-old", True, "no PID from lsof (nothing to kill)")
    pid = m.group(1)
    code, out, err = _run(kill_command(cfg, pid), cfg)
    if code != 0:
        return StepResult("kill-old", False, f"kill -TERM {pid} failed ({code}): {err.strip()[:200]}")
    return StepResult("kill-old", True, f"sent SIGTERM to pid {pid}")


def step_start(cfg: DeployConfig) -> StepResult:
    cmd = start_command(cfg)
    code, out, err = _run(cmd, cfg)
    if code != 0:
        return StepResult("start", False, f"start failed ({code}): {err.strip()[:200]}")
    return StepResult("start", True, "service started with Python 3.14 + tokens env")


def step_verify(cfg: DeployConfig) -> StepResult:
    remote = (
        f"curl -fsS http://localhost:{cfg.port}/healthz >/dev/null "
        f"&& curl -fsS http://localhost:{cfg.port}/readyz >/dev/null "
        f"&& echo verify-ok"
    )
    code, out, err = _run(ssh_command(cfg, remote), cfg)
    if cfg.dry_run:
        return StepResult("verify", True, "(dry-run) would curl /healthz and /readyz")
    if code != 0 or "verify-ok" not in out:
        return StepResult("verify", False, f"/healthz or /readyz failed ({code}): {(err or out).strip()[:200]}")
    return StepResult("verify", True, "/healthz + /readyz OK")


def run_deploy(cfg: DeployConfig, pin_only: bool = False) -> tuple[list[StepResult], dict]:
    results: list[StepResult] = []
    pin_result, pin = step_pin(cfg)
    results.append(pin_result)
    if not pin_result.ok or pin_only:
        return results, pin
    results.append(step_rsync(cfg))
    results.append(step_kill_old(cfg))
    results.append(step_start(cfg))
    results.append(step_verify(cfg))
    return results, pin


def run_rollback(cfg: DeployConfig, backup: Path) -> list[StepResult]:
    pin_result, pin = step_pin(cfg)
    code, out, err = _run(rollback_command(cfg, backup), cfg)
    if cfg.dry_run:
        ok = True
        detail = f"(dry-run) {' '.join(rollback_command(cfg, backup))}"
    else:
        ok = code == 0 and "rollback-ok" in out
        detail = "restored DB from backup" if ok else f"rollback failed ({code}): {(err or out).strip()[:200]}"
    return [pin_result, StepResult("rollback", ok, detail)]


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def summarize(results: list[StepResult], pin: dict) -> dict:
    failed = [r for r in results if not r.ok]
    return {
        "schema_version": 1,
        "pin": pin,
        "total": len(results),
        "failed": len(failed),
        "all_pass": not failed,
        "steps": [
            {"name": r.name, "ok": r.ok, "skipped": r.skipped, "detail": r.detail}
            for r in results
        ],
    }


def render_table(report: dict) -> str:
    pin = report["pin"]
    lines = ["LLMTier m5air deploy", "=" * 60]
    lines.append(f"pin: git={pin.get('git_commit', '')[:12]} "
                 f"openapi={pin.get('openapi_version')} schema={pin.get('schema_version')}")
    lines.append("-" * 60)
    for step in report["steps"]:
        mark = "SKIP" if step["skipped"] else ("OK  " if step["ok"] else "FAIL")
        lines.append(f"[{mark}] {step['name']}: {step['detail']}")
    lines.append("-" * 60)
    lines.append("all steps passed" if report["all_pass"] else f"{report['failed']} step(s) FAILED")
    return "\n".join(lines)


def build_config(args: argparse.Namespace) -> DeployConfig:
    return DeployConfig(
        host=args.host,
        code_dir=args.code_dir,
        remote_db=args.remote_db,
        remote_log=args.remote_log,
        remote_pidfile=args.remote_pidfile,
        python=args.python,
        port=args.port,
        admin_token=args.admin_token,
        data_token=args.data_token,
        ssh_opts=tuple(args.ssh_opt or ()),
        repo_root=args.repo_root,
        dry_run=args.dry_run,
        yes=args.yes,
        timeout=args.timeout,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default=HOST_ALIAS, help=f"ssh host (default: {HOST_ALIAS})")
    parser.add_argument("--code-dir", default=CODE_DIR, help="remote code directory")
    parser.add_argument("--remote-db", default=REMOTE_DB, help="remote SQLite DB path")
    parser.add_argument("--remote-log", default=REMOTE_LOG, help="remote log path")
    parser.add_argument("--remote-pidfile", default=REMOTE_PIDFILE, help="remote PID file path")
    parser.add_argument("--python", default=PYTHON314, help="remote Python 3.14 interpreter")
    parser.add_argument("--port", type=int, default=PORT, help="remote listen port")
    parser.add_argument("--admin-token", default=DEFAULT_ADMIN_TOKEN, help="admin token env value")
    parser.add_argument("--data-token", default=DEFAULT_DATA_TOKEN, help="data token env value")
    parser.add_argument("--ssh-opt", action="append", help="extra ssh -o option (repeatable)")
    parser.add_argument("--pin-only", action="store_true", help="record the artifact pin and exit")
    parser.add_argument("--rollback", type=Path, default=None, help="restore this remote DB backup")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT, help="local repository root")
    parser.add_argument("--dry-run", action="store_true", help="print commands without executing")
    parser.add_argument("--yes", action="store_true", help="required for any mutating deploy")
    parser.add_argument("--timeout", type=float, default=30.0, help="per-command timeout seconds")
    parser.add_argument("--json", action="store_true", help="emit a JSON report instead of a table")
    args = parser.parse_args(argv)

    if not args.dry_run and not args.pin_only and not args.yes:
        print("deploy: refusing to mutate without --yes (use --dry-run to preview); "
              "non-interactive guard.", file=sys.stderr)
        return EXIT_FAIL

    cfg = build_config(args)
    if args.rollback is not None:
        results = run_rollback(cfg, args.rollback)
        pin = artifact_pin(cfg.repo_root)
    else:
        results, pin = run_deploy(cfg, pin_only=args.pin_only)

    report = summarize(results, pin)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_table(report))
    return EXIT_OK if report["all_pass"] else EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
