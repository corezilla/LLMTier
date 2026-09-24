"""Feature: SSE stream wrapping for stream-stage fault injection.

Composition point: depends on the injection feature (enabled_stream_injection).
"""
from __future__ import annotations

from typing import Iterable

from .injections import InjectionDiagnostics

_MALFORMED_FRAME = b"event: response.malformed\ndata: {\"broken\": json-is-not-valid-here\n\n"


def stream_wrapper(injections: InjectionDiagnostics, deployment_id: str, base_stream: Iterable[bytes]) -> Iterable[bytes]:
    cfg = injections.enabled_stream_injection(deployment_id)
    if cfg is None:
        yield from base_stream
        return
    count = 0
    for chunk in base_stream:
        count += 1
        yield chunk
        if cfg["injection_type"] == "stream_terminate" and count >= (cfg["stream_terminate_after_events"] or 1):
            return
        if cfg["injection_type"] == "malformed_event" and count >= (cfg["malformed_after_events"] or 1):
            yield _MALFORMED_FRAME
            return
