#!/usr/bin/env python3
from __future__ import annotations

"""
llm_tier server - 独立 LLM 路由守护进程

启动:
    python -m tier_service --port 8765 --settings workspaces/my_project/settings.json

配置:
    --host        监听地址 (默认 127.0.0.1；可指定 private IP)
    --port        监听端口 (默认 8765)
    --settings    settings.json 路径
    TIER_SERVER_URL env var 也可配置客户端连接地址
"""

import argparse
import signal
import sys
import threading


# Purpose: Start the independent trusted-network Tier HTTP process from validated CLI arguments.
# Inputs: Process argv containing host, port, and optional settings path.
# Outputs: Process exit code after bounded listener shutdown.
def main() -> int:
    parser = argparse.ArgumentParser(
        description="llm_tier server - 独立 LLM 路由守护进程",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="监听地址：localhost、loopback 或明确 private IP (default: 127.0.0.1)",
    )
    parser.add_argument("--port", type=int, default=8765,
                        help="监听端口 (default: 8765)")
    parser.add_argument("--settings", default=None,
                        help="settings.json 路径")
    args = parser.parse_args()

    from server import TierServer

    server = TierServer(
        host=args.host,
        port=args.port,
        settings_path=args.settings,
    )

    print(f"llm_tier server starting on {args.host}:{args.port}",
          file=sys.stderr)
    if args.settings:
        print(f"  settings: {args.settings}", file=sys.stderr)

    stop_requested = threading.Event()

    # Purpose: Convert process termination signals into one graceful listener shutdown.
    # Inputs: POSIX signal number and current frame supplied by signal.signal.
    # Outputs: None; wakes the main wait loop.
    def request_stop(_signum: int, _frame: object) -> None:
        stop_requested.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    server.start(blocking=False)
    try:
        stop_requested.wait()
    finally:
        server.stop()

    return 0


if __name__ == "__main__":
    sys.exit(main())
