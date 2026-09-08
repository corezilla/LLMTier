from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
from pathlib import Path
from typing import Any

from client import TierClient


# Purpose: Build the sole operator command tree for existing Tier HTTP operations.
# Inputs: None.
# Outputs: Configured argparse parser.
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m cli", description="LLMTier operator CLI")
    parser.add_argument("--server-url", default="", help="Credential-free trusted Tier origin.")
    parser.add_argument("--output", choices=("json", "human"), default="json")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("health")
    subparsers.add_parser("runtime")
    subparsers.add_parser("debug")

    stats = subparsers.add_parser("stats")
    for name in ("project", "stage", "phase", "task-id", "task-key", "tier", "backend", "role"):
        stats.add_argument(f"--{name}", default="")

    invoke = subparsers.add_parser("invoke")
    invoke.add_argument("--request", required=True)

    reset = subparsers.add_parser("reset")
    reset.add_argument("--tier", default="")

    subparsers.add_parser("reload")

    probe = subparsers.add_parser("probe")
    probe.add_argument("--tier", required=True)
    probe.add_argument("--account", required=True)
    probe.add_argument("--backend", required=True)
    probe.add_argument("--model", required=True)
    return parser


# Purpose: Read one bounded JSON object used by a Tier write command.
# Inputs: Existing request path.
# Outputs: Parsed JSON object.
def load_request(path_value: str) -> dict[str, Any]:
    path = Path(path_value)
    if not path.is_file() or not 1 <= path.stat().st_size <= 10 * 1024 * 1024:
        raise ValueError("TIER_CLI_REQUEST_INVALID")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("TIER_CLI_REQUEST_INVALID")
    return payload


# Purpose: Convert parsed arguments into one existing Tier Client HTTP operation.
# Inputs: Parsed command namespace.
# Outputs: HTTP method, origin-relative path, and optional JSON body.
def command_request(args: argparse.Namespace) -> tuple[str, str, dict[str, Any] | None]:
    if args.command == "health":
        return "GET", "/health", None
    if args.command == "runtime":
        return "GET", "/runtime", None
    if args.command == "debug":
        return "GET", "/debug", None
    if args.command == "stats":
        params = {
            key: getattr(args, key)
            for key in ("project", "stage", "phase", "task_id", "task_key", "tier", "backend", "role")
            if getattr(args, key)
        }
        query = urllib.parse.urlencode(params)
        return "GET", f"/stats?{query}" if query else "/stats", None
    if args.command == "invoke":
        return "POST", "/call", load_request(args.request)
    if args.command == "reset":
        return "POST", "/reset", {"tier_name": args.tier}
    if args.command == "reload":
        return "POST", "/reload", {}
    if args.command == "probe":
        return (
            "POST",
            "/backend/probe",
            {
                "tier_name": args.tier,
                "account": args.account,
                "backend": args.backend,
                "model_name": args.model,
            },
        )
    raise ValueError("TIER_CLI_COMMAND_INVALID")


# Purpose: Map an HTTP response to the stable Tier CLI process exit range.
# Inputs: Upstream HTTP status and decoded response.
# Outputs: Process exit code.
def response_exit_code(status: int, payload: dict[str, Any]) -> int:
    if 200 <= status < 300 and payload.get("ok", True) is not False:
        return 0
    if status in {400, 422}:
        return 2
    if status == 404:
        return 4
    if status == 409:
        return 5
    if status in {408, 429, 500, 502, 503, 504}:
        return 3
    return 5


# Purpose: Render one Tier CLI result without creating a second result authority.
# Inputs: Output mode, response payload, and destination stream.
# Outputs: None.
def write_result(output_format: str, payload: dict[str, Any], stream: Any) -> None:
    if output_format == "json":
        stream.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        return
    for key in sorted(payload):
        stream.write(f"{key}: {payload[key]}\n")


# Purpose: Execute one Tier operator command through the existing TierClient transport.
# Inputs: Optional raw argv.
# Outputs: Stable process exit code with structured stdout or stderr.
def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        method, path, payload = command_request(args)
        status, response = TierClient(args.server_url).proxy_request(
            method,
            path,
            payload,
            timeout=10,
        )
        result = {"http_status": status, "operation": args.command, "response": response}
        exit_code = response_exit_code(status, response)
        write_result(args.output, result, sys.stdout if exit_code == 0 else sys.stderr)
        return exit_code
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        write_result(
            args.output,
            {"error_code": "TIER_CLI_ARGS_INVALID", "error_message": str(exc)},
            sys.stderr,
        )
        return 2
    except (TimeoutError, urllib.error.URLError, ConnectionError) as exc:
        write_result(
            args.output,
            {"error_code": "TIER_CLI_TRANSPORT_ERROR", "error_message": str(exc)},
            sys.stderr,
        )
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
