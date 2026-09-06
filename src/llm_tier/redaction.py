from __future__ import annotations

import re
from typing import Any


_SENSITIVE_KEY_PATTERN = re.compile(
    r"(?:api[_-]?key|authorization|cookie|secret|token|password|credential)",
    re.IGNORECASE,
)
_SENSITIVE_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)(\b(?:api[_-]?key|authorization|cookie|secret|token|password|credential)\b\s*[:=]\s*)"
    r"(?:bearer\s+)?([^\s,;]+)",
)
_BEARER_PATTERN = re.compile(r"(?i)(\bbearer\s+)([^\s,;]+)")


# Purpose: Redact credential-like values from one diagnostic text string.
# Inputs: Arbitrary text originating from a backend, exception, or trace field.
# Outputs: Text preserving diagnostic context while replacing secret values.
def redact_sensitive_text(value: Any) -> str:
    text = str(value or "")
    text = _SENSITIVE_ASSIGNMENT_PATTERN.sub(r"\1[REDACTED]", text)
    return _BEARER_PATTERN.sub(r"\1[REDACTED]", text)


# Purpose: Recursively redact sensitive values before public serialization or trace persistence.
# Inputs: Arbitrary JSON-compatible value and its optional parent field name.
# Outputs: A redacted copy that preserves the original container shape.
def redact_sensitive_value(value: Any, *, field_name: str = "") -> Any:
    if field_name and _SENSITIVE_KEY_PATTERN.search(field_name):
        return "[REDACTED]" if value not in (None, "") else value
    if isinstance(value, dict):
        return {
            str(key): redact_sensitive_value(item, field_name=str(key))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_sensitive_value(item) for item in value)
    if isinstance(value, str):
        return redact_sensitive_text(value)
    return value
