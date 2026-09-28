"""A 类 case 共用常量。

不在 conftest.py 里——pytest 不会通过 sys.path 提供 conftest 模块（设计上如此），
所以 from conftest import 在测试文件里直接 import 会失败。
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

FIXED_TIERS = ("Senior", "Junior", "Worker", "Associate", "Engineer", "Executor", "Embedding-v1")

M5AIR_BASE = "http://192.168.1.9:8181"
DATA_TOKEN = "dev-data"
ADMIN_TOKEN = "dev-admin"
OMLX_TOKEN = "9832"

# TS-003: provider *endpoints* must be LAN IPs, never 127.0.0.1 / localhost.
# Override with LLMTIER_TEST_PROVIDER_URL when the LAN upstream differs.
LAN_PROVIDER_ENDPOINT = os.environ.get(
    "LLMTIER_TEST_PROVIDER_URL", "http://192.168.1.9:9000/v1"
)


def recent_window(hours: int = 24 * 30) -> tuple[str, str]:
    """Return (from, to) RFC3339 UTC timestamps for the last ``hours`` hours."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)

    def fmt(value: datetime) -> str:
        return value.isoformat(timespec="seconds").replace("+00:00", "Z")

    return fmt(start), fmt(end)
