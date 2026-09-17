"""Semantic checks that JSON Schema alone cannot express for V0.3 candidate.5."""

from __future__ import annotations

import base64
import binascii
import math
import struct
from typing import Any


TERMINAL_EVENT_STATUS = {
    "response.completed": "completed",
    "response.incomplete": "incomplete",
    "response.failed": "failed",
}


def validate_sse_sequence(events: list[dict[str, Any]]) -> tuple[bool, str | None]:
    """Require monotonic sequence numbers, stable item IDs and exactly one final event."""
    if not events:
        return False, "stream_has_no_events"
    expected = 0
    terminal_seen = False
    item_ids: dict[int, str] = {}
    done_item_ids: dict[int, str] = {}
    done_items: dict[int, dict[str, Any]] = {}
    content_kinds: dict[int, str] = {}
    for event in events:
        if event.get("sequence_number") != expected:
            return False, "sequence_number_gap"
        expected += 1
        event_type = event.get("type")
        if terminal_seen:
            return False, "event_after_terminal"
        if event_type == "response.output_item.added":
            item = event.get("item", {})
            item_id = item.get("id")
            if not isinstance(item_id, str) or not item_id:
                return False, "output_item_id_missing"
            item_ids[event["output_index"]] = item_id
        elif event_type in {
            "response.output_text.delta",
            "response.refusal.delta",
            "response.reasoning_summary_text.delta",
            "response.reasoning_summary_part.done",
            "response.reasoning_text.delta",
        }:
            output_index = event.get("output_index")
            if output_index not in item_ids:
                return False, "delta_output_item_missing"
            if event_type == "response.output_text.delta":
                content_kinds[output_index] = "output_text"
            elif event_type == "response.refusal.delta":
                content_kinds[output_index] = "refusal"
        elif event_type in {
            "response.function_call_arguments.delta",
            "response.function_call_arguments.done",
        }:
            output_index = event.get("output_index")
            if item_ids.get(output_index) != event.get("item_id"):
                return False, "delta_item_id_mismatch"
        elif event_type == "response.output_item.done":
            item = event.get("item", {})
            output_index = event["output_index"]
            if item_ids.get(output_index) != item.get("id"):
                return False, "output_item_id_changed"
            done_item_ids[output_index] = item["id"]
            done_items[output_index] = item
            content_kind = content_kinds.get(output_index)
            if content_kind is not None:
                content = item.get("content", [])
                if not any(part.get("type") == content_kind for part in content):
                    return False, "output_content_kind_mismatch"
        elif event_type in TERMINAL_EVENT_STATUS:
            response = event.get("response", {})
            if response.get("status") != TERMINAL_EVENT_STATUS[event_type]:
                return False, "terminal_event_status_mismatch"
            terminal_ids = {
                index: item.get("id")
                for index, item in enumerate(response.get("output", []))
            }
            if terminal_ids != done_item_ids:
                return False, "terminal_output_identity_mismatch"
            terminal_items = {
                index: item
                for index, item in enumerate(response.get("output", []))
            }
            if terminal_items != done_items:
                return False, "terminal_output_item_mismatch"
            terminal_seen = True
        elif event_type == "error":
            terminal_seen = True
    if not terminal_seen:
        return False, "stream_ended_without_terminal_event"
    return True, None


def validate_usage_record(record: dict[str, Any]) -> tuple[bool, str | None]:
    """Unknown token facts must be null; known totals must be internally consistent."""
    token_fields = (
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "cached_input_tokens",
        "cache_write_tokens",
        "reasoning_tokens",
    )
    if record.get("measurement_status") == "unknown":
        if record.get("source") != "unavailable":
            return False, "unknown_source_must_be_unavailable"
        if any(record.get(field) is not None for field in token_fields):
            return False, "unknown_tokens_must_be_null"
        return True, None
    expected_source = {
        "measured": "provider",
        "estimated": "gateway_estimate",
    }.get(record.get("measurement_status"))
    if expected_source is None or record.get("source") != expected_source:
        return False, "measurement_source_mismatch"
    required = ("input_tokens", "output_tokens", "total_tokens")
    if any(not isinstance(record.get(field), int) for field in required):
        return False, "known_totals_must_be_integers"
    if record["total_tokens"] != record["input_tokens"] + record["output_tokens"]:
        return False, "total_tokens_mismatch"
    cached = record.get("cached_input_tokens")
    if cached is not None and cached > record["input_tokens"]:
        return False, "cached_input_exceeds_input"
    reasoning = record.get("reasoning_tokens")
    if reasoning is not None and reasoning > record["output_tokens"]:
        return False, "reasoning_exceeds_output"
    return True, None


def validate_usage_transition(
    previous: dict[str, Any], candidate: dict[str, Any]
) -> tuple[bool, str | None]:
    """Reject duplicate or decreasing versions and final/quality regressions."""
    if previous.get("request_id") != candidate.get("request_id"):
        return False, "request_id_changed"
    if candidate.get("record_version", 0) <= previous.get("record_version", 0):
        return False, "record_version_not_increasing"
    if previous.get("is_final") and not candidate.get("is_final"):
        return False, "final_record_regression"
    rank = {"unknown": 0, "estimated": 1, "measured": 2}
    if rank.get(candidate.get("measurement_status"), -1) < rank.get(
        previous.get("measurement_status"), -1
    ):
        return False, "measurement_quality_regression"
    return True, None


def select_usage_replacement(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Choose one highest-version fact for one request ID; never add revisions."""
    if not records:
        raise ValueError("records must not be empty")
    request_ids = {record["request_id"] for record in records}
    if len(request_ids) != 1:
        raise ValueError("records must have one request_id")
    versions = [record["record_version"] for record in records]
    if len(versions) != len(set(versions)):
        raise ValueError("record_version must be unique")
    return max(records, key=lambda record: record["record_version"])


def execute_usage_design_sequence(steps: list[dict[str, Any]]) -> tuple[bool, str | None]:
    """Execute the candidate's pure design model for snapshots and durable unknowns."""
    snapshots: dict[str, list[dict[str, Any]]] = {}
    obligations: dict[str, dict[str, Any]] = {}
    dispatched: set[str] = set()
    for step in steps:
        action = step["action"]
        if action == "create_snapshot":
            snapshots[step["snapshot_id"]] = [dict(member) for member in step["members"]]
        elif action in {"append_revision", "append_record"}:
            # Immutable revisions and new rows do not mutate an existing snapshot.
            continue
        elif action == "read_next_page":
            actual = snapshots.get(step["snapshot_id"])
            expected = step["expected_members"]
            if actual is None or actual[-len(expected):] != expected:
                return False, "snapshot_members_changed"
        elif action == "insert_usage_obligation":
            obligations[step["request_id"]] = {
                key: value for key, value in step.items() if key != "action"
            }
        elif action == "provider_dispatch":
            pending = [request_id for request_id in obligations if request_id not in dispatched]
            if not pending:
                return False, "dispatch_without_usage_obligation"
            dispatched.add(pending[-1])
        elif action == "process_crash_before_measurement_update":
            continue
        elif action == "restart_and_query":
            if obligations.get(step["expected_record"]["request_id"]) != step["expected_record"]:
                return False, "durable_unknown_missing_after_restart"
        else:
            return False, "unknown_usage_design_action"
    return True, None


def validate_embedding_response(
    request: dict[str, Any], response: dict[str, Any], allowed_dimensions: set[int]
) -> tuple[bool, str | None]:
    """Validate the consumer-critical vector count, indices, dimensions and finite values."""
    raw_input = request.get("input")
    expected_count = len(raw_input) if isinstance(raw_input, list) else 1
    items = response.get("data")
    if not isinstance(items, list) or len(items) != expected_count:
        return False, "embedding_count_mismatch"
    indices = [item.get("index") for item in items]
    if sorted(indices) != list(range(expected_count)) or len(set(indices)) != expected_count:
        return False, "embedding_index_mismatch"
    requested_dimension = request.get("dimensions")
    observed_dimension: int | None = None
    expected_encoding = request.get("encoding_format", "float")
    for item in items:
        encoded_vector = item.get("embedding")
        if expected_encoding == "float":
            if not isinstance(encoded_vector, list) or not encoded_vector:
                return False, "embedding_representation_mismatch"
            vector = encoded_vector
        elif expected_encoding == "base64":
            if not isinstance(encoded_vector, str) or not encoded_vector:
                return False, "embedding_representation_mismatch"
            try:
                raw = base64.b64decode(encoded_vector, validate=True)
            except (binascii.Error, ValueError):
                return False, "embedding_base64_invalid"
            if not raw or len(raw) % 4 != 0:
                return False, "embedding_base64_length_invalid"
            vector = list(struct.unpack(f"<{len(raw) // 4}f", raw))
        else:
            return False, "embedding_encoding_unsupported"
        if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in vector):
            return False, "embedding_value_not_finite"
        if observed_dimension is None:
            observed_dimension = len(vector)
        elif len(vector) != observed_dimension:
            return False, "embedding_dimension_inconsistent"
    if observed_dimension not in allowed_dimensions:
        return False, "embedding_dimension_not_advertised"
    if requested_dimension is not None and observed_dimension != requested_dimension:
        return False, "embedding_dimension_mismatch"
    return True, None
