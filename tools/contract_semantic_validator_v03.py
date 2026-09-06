from __future__ import annotations

from datetime import datetime
from typing import Any


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def validate_metadata(metadata: dict[str, str]) -> tuple[bool, str | None]:
    if len(metadata) > 16:
        return False, "metadata_too_many_pairs"
    for key, value in metadata.items():
        if len(key.encode("utf-8")) > 64:
            return False, "metadata_key_too_large"
        if len(value.encode("utf-8")) > 512:
            return False, "metadata_value_too_large"
    return True, None


def validate_capacity_snapshot(snapshot: dict[str, Any]) -> tuple[bool, str | None]:
    groups = snapshot["capacity_groups"]
    levels = snapshot["service_levels"]
    group_ids = [item["capacity_group_id"] for item in groups]
    level_ids = [item["service_level_id"] for item in levels]

    if len(group_ids) != len(set(group_ids)):
        return False, "duplicate_capacity_group_id"
    if len(level_ids) != len(set(level_ids)):
        return False, "duplicate_service_level_id"

    group_map = {item["capacity_group_id"]: item for item in groups}
    level_map = {item["service_level_id"]: item for item in levels}
    for group in groups:
        if group["available_committed_concurrency"] > group["committed_concurrency"]:
            return False, "available_exceeds_committed"
        for level_id in group["member_service_level_ids"]:
            if level_id not in level_map or group["capacity_group_id"] not in level_map[level_id]["capacity_group_ids"]:
                return False, "capacity_membership_mismatch"
    for level in levels:
        for group_id in level["capacity_group_ids"]:
            if group_id not in group_map or level["service_level_id"] not in group_map[group_id]["member_service_level_ids"]:
                return False, "capacity_membership_mismatch"

    if _parse_time(snapshot["observed_at"]) >= _parse_time(snapshot["valid_until"]):
        return False, "invalid_snapshot_time_window"
    return True, None


def validate_projection(snapshot: dict[str, Any], requested_seats: dict[str, int]) -> tuple[bool, str | None]:
    valid, code = validate_capacity_snapshot(snapshot)
    if not valid:
        return False, code
    levels = {item["service_level_id"]: item for item in snapshot["service_levels"]}
    for level_id, seats in requested_seats.items():
        level = levels[level_id]
        quota = level["request_quota_remaining"]
        if quota is None:
            return False, "client_quota_unknown"
        if seats > quota:
            return False, "client_quota_exhausted"
    return True, None
