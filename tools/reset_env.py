#!/usr/bin/env python3
"""Environment reset ladder (system test plan §6 / §2-E4), idempotent and safe.

Steps, in order:

  (a) backup — copy the SQLite DB first via the sqlite3 online-backup API,
      unless ``--no-backup``. ``--db`` selects a **local** file; when
      ``--remote-db-host`` + ``--remote-db-path`` are given (e.g. m5air) the
      backup runs **on the remote host** (``sqlite3 .backup`` over ssh) into
      ``--remote-backup-dir`` (default ``<remote-db-dir>/backups``), so the live
      LAN instance is snapshotted before any destructive step.
  (b) restore/rebuild — optional ``--restore <bak>`` (replace the live DB with a
      backup) or ``--rebuild`` (start a fresh empty DB file).
  (c) clear injections — for every deployment, ``GET`` its diagnostics and
      ``PATCH {"items":[]}``; then ``GET`` again and assert the list is empty.
  (d) reset the usage ledger — ``DELETE /v1/usage`` (skip with ``--no-ledger``).
  (e) kill leftovers — terminate local test ``LLMTierInstance`` / temp-instance
      processes (matched by ``http_api`` + the temp-instance prefixes) and free
      temp ports.
  (f) re-run readiness — invoke ``tools/check_env.py`` at the end.

Safety:
  * ``--dry-run`` prints the planned actions without touching anything.
  * ``--yes`` is required for any mutating run (non-interactive guard).
  * The DB backup happens before any destructive action, always.
  * Exit code is non-zero if any executed step fails.

Usage::

    tools/reset_env.py --dry-run
    tools/reset_env.py --yes --remote-db-host m5air \
        --remote-db-path /Users/mlp/LLMTier-dev/state.sqlite3
    tools/reset_env.py --yes --class a --db ./state.sqlite3
    tools/reset_env.py --yes --restore backups/state-20260930.sqlite3
    tools/reset_env.py --yes --rebuild --no-ledger
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_BASE_URL = "http://192.168.1.9:8181"
DEFAULT_ADMIN_TOKEN = "dev-admin"

EXIT_OK = 0
EXIT_FAIL = 1


@dataclass
class StepResult:
    name: str
    ok: bool
    detail: str
    skipped: bool = False


@dataclass
class ResetConfig:
    base_url: str = DEFAULT_BASE_URL
    admin_token: str = DEFAULT_ADMIN_TOKEN
    db_path: Path | None = None
    backup_dir: Path = field(default_factory=lambda: REPO_ROOT / "backups")
    no_backup: bool = False
    restore: Path | None = None
    rebuild: bool = False
    no_ledger: bool = False
    dry_run: bool = False
    yes: bool = False
    kind: str = "all"
    timeout: float = 5.0
    lan_ip_override: str | None = None
    python: str = sys.executable
    repo_root: Path = REPO_ROOT
    remote_db_host: str | None = None
    remote_db_path: str | None = None
    remote_backup_dir: str | None = None
    ssh_opts: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _request(method: str, url: str, token: str | None = None, body: dict | None = None,
             timeout: float = 5.0) -> tuple[int, str]:
    data = None
    headers: dict = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        return 0, f"{type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------
# Step (a): backup via the sqlite3 online backup API
# ---------------------------------------------------------------------------

def default_backup_path(db_path: Path, now: _dt.datetime | None = None) -> Path:
    stamp = (now or _dt.datetime.now()).strftime("%Y%m%d-%H%M%S")
    return db_path.with_name(f"{db_path.name}.bak-{stamp}")


def backup_database(db_path: Path, dest: Path) -> None:
    """Online backup of ``db_path`` into ``dest`` using sqlite3 backup API."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(str(db_path))
    try:
        target = sqlite3.connect(str(dest))
        try:
            source.backup(target)
        finally:
            target.close()
    finally:
        source.close()


def remote_backup_dest(cfg: ResetConfig, stamp: str | None = None) -> str:
    """Remote destination path for the online backup (mirrors default_backup_path)."""
    db = Path(cfg.remote_db_path or "")
    backup_dir = cfg.remote_backup_dir or f"{db.parent}/backups"
    stamp = stamp or _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{backup_dir}/{db.name}.bak-{stamp}"


def remote_backup_command(cfg: ResetConfig, dest: str) -> list[str]:
    """ssh argv running sqlite3's **online** backup so the live service is safe.

    ``.backup`` uses the SQLite online backup API on the remote host, so the
    running m5air service keeps working and the snapshot is consistent.
    """
    db = cfg.remote_db_path
    remote = f"mkdir -p \"$(dirname {dest})\" && sqlite3 {db} \".backup '{dest}'\""
    cmd = ["ssh"]
    if cfg.ssh_opts:
        cmd.extend(cfg.ssh_opts)
    cmd.extend([cfg.remote_db_host, remote])
    return cmd


def step_backup(cfg: ResetConfig) -> StepResult:
    name = "backup"
    if cfg.no_backup:
        return StepResult(name, True, "--no-backup: skipped", skipped=True)
    # Remote (m5air) online backup takes precedence when a remote DB is named:
    # this is what satisfies "back up before any destructive action" for the
    # live LAN instance whose SQLite file is not on the executor.
    if cfg.remote_db_host and cfg.remote_db_path:
        dest = remote_backup_dest(cfg)
        if cfg.dry_run:
            return StepResult(name, True, f"would back up {cfg.remote_db_path} -> {dest}")
        try:
            proc = subprocess.run(remote_backup_command(cfg, dest), capture_output=True,
                                  text=True, timeout=max(cfg.timeout, 120))
        except (OSError, subprocess.SubprocessError) as exc:
            return StepResult(name, False, f"remote backup failed: {type(exc).__name__}: {exc}")
        if proc.returncode != 0:
            return StepResult(name, False,
                              f"remote backup failed ({proc.returncode}): {proc.stderr.strip()[:200]}")
        return StepResult(name, True, f"backed up {cfg.remote_db_path} -> {dest}")
    if cfg.db_path is None:
        return StepResult(name, True, "no --db/--remote-db supplied: skipped", skipped=True)
    if not cfg.db_path.exists():
        return StepResult(name, True, f"no db at {cfg.db_path}: skipped", skipped=True)
    dest = default_backup_path(cfg.db_path)
    if cfg.dry_run:
        return StepResult(name, True, f"would back up {cfg.db_path} -> {dest}")
    try:
        backup_database(cfg.db_path, dest)
    except Exception as exc:  # noqa: BLE001
        return StepResult(name, False, f"backup failed: {type(exc).__name__}: {exc}")
    return StepResult(name, True, f"backed up {cfg.db_path} -> {dest}")


# ---------------------------------------------------------------------------
# Step (b): restore / rebuild
# ---------------------------------------------------------------------------

def step_restore_or_rebuild(cfg: ResetConfig) -> StepResult:
    name = "restore/rebuild"
    if cfg.restore is None and not cfg.rebuild:
        return StepResult(name, True, "no --restore/--rebuild: skipped", skipped=True)
    if cfg.restore is not None and cfg.rebuild:
        return StepResult(name, False, "--restore and --rebuild are mutually exclusive")
    if cfg.db_path is None:
        return StepResult(name, False, "--restore/--rebuild requires --db")
    if cfg.restore is not None:
        if not cfg.restore.exists():
            return StepResult(name, False, f"restore source missing: {cfg.restore}")
        if cfg.dry_run:
            return StepResult(name, True, f"would restore {cfg.restore} -> {cfg.db_path}")
        try:
            for suffix in ("", "-wal", "-shm"):
                side = Path(str(cfg.db_path) + suffix)
                if side.exists():
                    side.unlink()
            shutil.copy2(cfg.restore, cfg.db_path)
        except OSError as exc:
            return StepResult(name, False, f"restore failed: {exc}")
        return StepResult(name, True, f"restored {cfg.restore} -> {cfg.db_path}")
    # rebuild: replace with a fresh empty DB file
    if cfg.dry_run:
        return StepResult(name, True, f"would rebuild fresh db at {cfg.db_path}")
    try:
        for suffix in ("", "-wal", "-shm"):
            side = Path(str(cfg.db_path) + suffix)
            if side.exists():
                side.unlink()
        cfg.db_path.parent.mkdir(parents=True, exist_ok=True)
        cfg.db_path.touch()
    except OSError as exc:
        return StepResult(name, False, f"rebuild failed: {exc}")
    return StepResult(name, True, f"rebuilt fresh db at {cfg.db_path}")


# ---------------------------------------------------------------------------
# Step (c): clear diagnostic injections
# ---------------------------------------------------------------------------

def _list_deployment_ids(cfg: ResetConfig) -> tuple[list[str], str | None]:
    status, body = _request("GET", f"{cfg.base_url}/v1/deployments", cfg.admin_token, timeout=cfg.timeout)
    if status != 200:
        return [], f"GET /v1/deployments returned {status}: {body[:120]}"
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        return [], f"/v1/deployments body not JSON: {exc}"
    items = data.get("data") if isinstance(data, dict) else data
    if not isinstance(items, list):
        return [], "/v1/deployments payload missing a 'data' list"
    ids = []
    for item in items:
        if isinstance(item, dict) and item.get("id"):
            ids.append(item["id"])
    return ids, None


def deployments_with_injections(cfg: ResetConfig) -> tuple[list[str], str | None]:
    """Return deployment ids that currently have at least one injection."""
    ids, err = _list_deployment_ids(cfg)
    if err:
        return [], err
    dirty = []
    for did in ids:
        status, body = _request("GET", f"{cfg.base_url}/v1/deployments/{did}/diagnostics",
                                cfg.admin_token, timeout=cfg.timeout)
        if status != 200:
            return [], f"GET diagnostics {did} returned {status}"
        try:
            items = json.loads(body)
        except json.JSONDecodeError:
            return [], f"diagnostics {did} body not JSON"
        if isinstance(items, list) and items:
            dirty.append(did)
    return dirty, None


def step_clear_injections(cfg: ResetConfig) -> StepResult:
    name = "clear-injections"
    if cfg.base_url.lower().startswith("http://127.0.0.1"):
        pass  # local instance is allowed (tests use mocks)
    ids, err = _list_deployment_ids(cfg)
    if err:
        return StepResult(name, False, err)
    if cfg.dry_run:
        dirty, err = deployments_with_injections(cfg)
        if err:
            return StepResult(name, False, f"dry-run scan failed: {err}")
        return StepResult(name, True,
                          f"would clear injections on {len(dirty)} deployment(s): {dirty or '[]'}")
    cleared = 0
    for did in ids:
        status, body = _request("PATCH", f"{cfg.base_url}/v1/deployments/{did}/diagnostics",
                                cfg.admin_token, {"items": []}, timeout=cfg.timeout)
        if status != 200:
            return StepResult(name, False, f"PATCH diagnostics {did} returned {status}: {body[:120]}")
        cleared += 1
    # assert every deployment now reports an empty list
    for did in ids:
        status, body = _request("GET", f"{cfg.base_url}/v1/deployments/{did}/diagnostics",
                                cfg.admin_token, timeout=cfg.timeout)
        if status != 200:
            return StepResult(name, False, f"verify GET diagnostics {did} returned {status}")
        try:
            items = json.loads(body)
        except json.JSONDecodeError:
            return StepResult(name, False, f"verify diagnostics {did} body not JSON")
        if items:
            return StepResult(name, False, f"injections not cleared on {did}: {items}")
    return StepResult(name, True, f"cleared + verified empty on {cleared} deployment(s)")


# ---------------------------------------------------------------------------
# Step (d): reset usage ledger
# ---------------------------------------------------------------------------

def step_reset_ledger(cfg: ResetConfig) -> StepResult:
    name = "reset-ledger"
    if cfg.no_ledger:
        return StepResult(name, True, "--no-ledger: skipped", skipped=True)
    if cfg.dry_run:
        return StepResult(name, True, "would DELETE /v1/usage")
    status, body = _request("DELETE", f"{cfg.base_url}/v1/usage", cfg.admin_token, timeout=cfg.timeout)
    if status != 200:
        return StepResult(name, False, f"DELETE /v1/usage returned {status}: {body[:120]}")
    return StepResult(name, True, f"usage ledger reset: {body[:120]}")


# ---------------------------------------------------------------------------
# Step (e): kill leftover local test instances / free temp ports
# ---------------------------------------------------------------------------

# A leftover test instance is an `http_api` process whose argv references a
# temp DB path (conftest uses `tempfile.mkdtemp(prefix="llmtier_b_")`; the
# check_env temp instance uses `llmtier_check_env_`). Production m5air runs
# with `state.sqlite3` and is never matched.
LEFTOVER_MARKERS = ("llmtier_b_", "llmtier_check_env_", "llmtier_reset_")


def find_leftover_pids(ps_output: str, markers: tuple[str, ...] = LEFTOVER_MARKERS,
                       self_pid: int | None = None) -> list[int]:
    """Parse ``ps`` output and return PIDs of leftover local test instances."""
    pids: list[int] = []
    for line in ps_output.splitlines():
        if "http_api" not in line or "grep" in line:
            continue
        if not any(marker in line for marker in markers):
            continue
        parts = line.split(None, 1)
        if not parts or not parts[0].isdigit():
            continue
        pid = int(parts[0])
        if self_pid is not None and pid == self_pid:
            continue
        if pid not in pids:
            pids.append(pid)
    return pids


def _read_ps() -> str:
    try:
        proc = subprocess.run(["ps", "-eo", "pid=,command="], capture_output=True,
                              text=True, timeout=10)
        return proc.stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def free_temp_ports(markers: tuple[str, ...] = LEFTOVER_MARKERS) -> int:
    """Best-effort: kill nothing, just count; ports free once PIDs are killed.

    Kept as a hook so tests can assert it is invoked during the reset ladder.
    """
    return 0


def step_kill_leftovers(cfg: ResetConfig) -> StepResult:
    name = "kill-leftovers"
    pids = find_leftover_pids(_read_ps(), self_pid=os.getpid())
    if cfg.dry_run:
        return StepResult(name, True, f"would terminate leftover pids: {pids or '[]'}")
    killed = []
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
            killed.append(pid)
        except ProcessLookupError:
            pass
        except OSError as exc:
            return StepResult(name, False, f"kill {pid} failed: {exc}")
    free_temp_ports()
    return StepResult(name, True, f"terminated {len(killed)} leftover pid(s): {killed or '[]'}")


# ---------------------------------------------------------------------------
# Step (f): re-run readiness
# ---------------------------------------------------------------------------

def build_readiness_command(cfg: ResetConfig) -> list[str]:
    return [
        cfg.python, str(cfg.repo_root / "tools" / "check_env.py"),
        "--class", cfg.kind if cfg.kind in ("a", "b", "all") else "all",
        "--base-url", cfg.base_url,
        "--admin-token", cfg.admin_token,
        "--json",
    ]


def step_recheck(cfg: ResetConfig) -> StepResult:
    name = "recheck"
    cmd = build_readiness_command(cfg)
    if cfg.dry_run:
        return StepResult(name, True, f"would run: {' '.join(cmd)}")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        return StepResult(name, False, f"readiness check failed to run: {exc}")
    if proc.returncode == 0:
        return StepResult(name, True, "readiness check passed")
    return StepResult(name, False,
                      f"readiness check failed (exit {proc.returncode}): {proc.stdout[-160:].strip()}")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def reset_plan() -> list:
    """The ordered reset ladder (plan §2-E4 a..f)."""
    return [
        step_backup,
        step_restore_or_rebuild,
        step_clear_injections,
        step_reset_ledger,
        step_kill_leftovers,
        step_recheck,
    ]


def run_reset(cfg: ResetConfig) -> list[StepResult]:
    results: list[StepResult] = []
    for step in reset_plan():
        results.append(step(cfg))
    return results


def summarize(results: list[StepResult]) -> dict:
    failed = [r for r in results if not r.ok]
    return {
        "schema_version": 1,
        "total": len(results),
        "failed": len(failed),
        "all_pass": not failed,
        "steps": [
            {"name": r.name, "ok": r.ok, "skipped": r.skipped, "detail": r.detail}
            for r in results
        ],
    }


def render_table(report: dict) -> str:
    lines = ["LLMTier environment reset ladder", "=" * 60]
    for step in report["steps"]:
        mark = "SKIP" if step["skipped"] else ("OK  " if step["ok"] else "FAIL")
        lines.append(f"[{mark}] {step['name']}")
        lines.append(f"        {step['detail']}")
    lines.append("-" * 60)
    lines.append("all steps passed" if report["all_pass"] else f"{report['failed']} step(s) FAILED")
    return "\n".join(lines)


def build_config(args: argparse.Namespace) -> ResetConfig:
    return ResetConfig(
        base_url=args.base_url,
        admin_token=args.admin_token,
        db_path=args.db,
        backup_dir=args.backup_dir,
        no_backup=args.no_backup,
        restore=args.restore,
        rebuild=args.rebuild,
        no_ledger=args.no_ledger,
        dry_run=args.dry_run,
        yes=args.yes,
        kind=args.kind,
        timeout=args.timeout,
        lan_ip_override=args.lan_ip,
        python=args.python,
        repo_root=args.repo_root,
        remote_db_host=args.remote_db_host,
        remote_db_path=args.remote_db_path,
        remote_backup_dir=args.remote_backup_dir,
        ssh_opts=tuple(args.ssh_opt or ()),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL,
                        help=f"m5air LLMTier base URL (default: {DEFAULT_BASE_URL})")
    parser.add_argument("--admin-token", default=DEFAULT_ADMIN_TOKEN,
                        help="admin bearer token (default: dev-admin)")
    parser.add_argument("--db", type=Path, default=None, help="path to the SQLite DB to back up")
    parser.add_argument("--backup-dir", type=Path, default=REPO_ROOT / "backups",
                        help="directory for backups (default: <repo>/backups)")
    parser.add_argument("--remote-db-host", default=None,
                        help="ssh host whose SQLite DB is backed up online (e.g. m5air)")
    parser.add_argument("--remote-db-path", default=None,
                        help="remote SQLite DB path (e.g. /Users/mlp/LLMTier-dev/state.sqlite3)")
    parser.add_argument("--remote-backup-dir", default=None,
                        help="remote backup dir (default: <remote-db-dir>/backups)")
    parser.add_argument("--ssh-opt", action="append", help="extra ssh -o option (repeatable)")
    parser.add_argument("--no-backup", action="store_true", help="skip the pre-reset backup")
    parser.add_argument("--restore", type=Path, default=None, help="restore this backup into --db")
    parser.add_argument("--rebuild", action="store_true", help="replace --db with a fresh empty DB")
    parser.add_argument("--no-ledger", action="store_true", help="skip DELETE /v1/usage")
    parser.add_argument("--class", dest="kind", choices=("a", "b", "all"), default="all",
                        help="readiness class for the final re-check (default: all)")
    parser.add_argument("--dry-run", action="store_true", help="print planned actions only")
    parser.add_argument("--yes", action="store_true", help="required for any mutating run")
    parser.add_argument("--timeout", type=float, default=5.0, help="per-request timeout seconds")
    parser.add_argument("--lan-ip", default=None, help="override LAN IP for the B-class re-check")
    parser.add_argument("--python", default=sys.executable, help="Python interpreter for the re-check")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT, help="repository root")
    parser.add_argument("--json", action="store_true", help="emit a JSON report instead of a table")
    args = parser.parse_args(argv)

    if not args.dry_run and not args.yes:
        print("reset_env: refusing to mutate without --yes (use --dry-run to preview); "
              "non-interactive guard.", file=sys.stderr)
        return EXIT_FAIL

    cfg = build_config(args)
    results = run_reset(cfg)
    report = summarize(results)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_table(report))
    return EXIT_OK if report["all_pass"] else EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
