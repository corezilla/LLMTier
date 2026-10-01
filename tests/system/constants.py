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

    return iso_sec(start), iso_sec(end)


def iso_sec(value: datetime) -> str:
    """RFC3339 UTC, second precision, ``Z`` suffix (the query-param form)."""
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def iso_ms(value: datetime) -> str:
    """RFC3339 UTC, millisecond precision, ``Z`` suffix (the storage form)."""
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_ts(value: str) -> datetime:
    """Parse an RFC3339 timestamp (``Z`` or offset form) to an aware datetime."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


# OpenAPI UsageRecord required keys (additionalProperties:false adds the three
# optional token-detail keys, which the implementation always emits).
USAGE_RECORD_REQUIRED_KEYS = {
    "request_id",
    "record_version",
    "is_final",
    "model",
    "endpoint",
    "recorded_at",
    "updated_at",
    "measurement_status",
    "source",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "cached_input_tokens",
}
USAGE_RECORD_OPTIONAL_KEYS = {"cache_write_tokens", "reasoning_tokens"}
USAGE_RECORD_KEYS = USAGE_RECORD_REQUIRED_KEYS | USAGE_RECORD_OPTIONAL_KEYS

USAGE_ENDPOINTS = {"/v1/responses", "/v1/embeddings"}
MEASUREMENT_STATUSES = {"measured", "estimated", "unknown"}
USAGE_SOURCES = {"provider", "gateway_estimate", "unavailable"}
USAGE_PAGE_KEYS = {"data", "next_cursor", "has_more", "snapshot_id", "snapshot_at"}


def assert_usage_record(record: dict, *, where: str = "record") -> None:
    """Assert one UsageRecord satisfies the OpenAPI wire contract.

    Enforces the required key set, endpoint/status/source enums, RFC3339
    timestamps, the `unknown ⇒ all token fields null` invariant (INV-5) and the
    else-branch rule that measured/estimated carries non-null integer tokens.
    The optional token-detail keys, when present, must be int-or-null.
    """
    missing = USAGE_RECORD_REQUIRED_KEYS - set(record)
    assert not missing, f"{where} 缺 UsageRecord 必填键: {sorted(missing)}"
    extra = set(record) - USAGE_RECORD_KEYS
    assert not extra, f"{where} 含未知键: {sorted(extra)}"

    assert isinstance(record["request_id"], str) and record["request_id"], f"{where} request_id 非法"
    assert isinstance(record["record_version"], int) and not isinstance(record["record_version"], bool)
    assert record["record_version"] >= 1, f"{where} record_version < 1: {record['record_version']}"
    assert isinstance(record["is_final"], bool), f"{where} is_final 非 bool"
    assert isinstance(record["model"], str) and record["model"], f"{where} model 非法"
    assert record["endpoint"] in USAGE_ENDPOINTS, f"{where} endpoint 枚举不符: {record['endpoint']!r}"
    parse_ts(record["recorded_at"]); parse_ts(record["updated_at"])
    status = record["measurement_status"]
    assert status in MEASUREMENT_STATUSES, f"{where} measurement_status 枚举不符: {status!r}"
    assert record["source"] in USAGE_SOURCES, f"{where} source 枚举不符: {record['source']!r}"

    tokens = ("input_tokens", "output_tokens", "total_tokens", "cached_input_tokens")
    if status == "unknown":
        assert record["source"] == "unavailable", f"{where} unknown 必须 source=unavailable: {record}"
        for key in tokens + ("cache_write_tokens", "reasoning_tokens"):
            if key in record:
                assert record[key] is None, f"{where} unknown ⇒ {key} 必须为 null（非 0）: {record[key]!r}"
    elif status == "measured":
        assert record["source"] == "provider", f"{where} measured 必须 source=provider: {record}"
    elif status == "estimated":
        assert record["source"] == "gateway_estimate", f"{where} estimated 必须 source=gateway_estimate: {record}"

    for key in USAGE_RECORD_OPTIONAL_KEYS:
        if key in record and record[key] is not None:
            assert isinstance(record[key], int) and not isinstance(record[key], bool), (
                f"{where} {key} 非整数: {record[key]!r}"
            )
