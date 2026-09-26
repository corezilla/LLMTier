from __future__ import annotations

import json
from typing import Iterable


def frame(event: str, data: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, separators=(',', ':'))}\n\n".encode()


def response_stream(response: dict) -> Iterable[bytes]:
    sequence = 0
    def event(name: str, payload: dict) -> bytes:
        nonlocal sequence
        payload["sequence_number"] = sequence
        sequence += 1
        return frame(name, payload)
    created = dict(response)
    created["status"] = "in_progress"
    created["output"] = []
    created["usage"] = None
    yield event("response.created", {"type": "response.created", "response": created})
    for index, item in enumerate(response["output"]):
        yield event("response.output_item.added", {"type": "response.output_item.added", "output_index": index, "item": item})
        if item.get("type") == "message":
            for content_index, content in enumerate(item.get("content", [])):
                if content.get("type") == "output_text":
                    yield event("response.output_text.delta", {"type": "response.output_text.delta", "item_id": item["id"], "output_index": index, "content_index": content_index, "delta": content["text"]})
                elif content.get("type") == "refusal":
                    yield event("response.refusal.delta", {"type": "response.refusal.delta", "item_id": item["id"], "output_index": index, "content_index": content_index, "delta": content["refusal"]})
        elif item.get("type") == "reasoning":
            for content_index, content in enumerate(item.get("content", [])):
                if content.get("type") == "reasoning_text":
                    yield event("response.reasoning_text.delta", {"type": "response.reasoning_text.delta", "item_id": item["id"], "output_index": index, "content_index": content_index, "delta": content["text"]})
            for s_index, summary_item in enumerate(item.get("summary", []) or []):
                if isinstance(summary_item, dict) and summary_item.get("type") == "summary_text":
                    yield event("response.reasoning_summary_text.delta", {"type": "response.reasoning_summary_text.delta", "item_id": item["id"], "output_index": index, "summary_index": s_index, "delta": summary_item["text"]})
                    yield event("response.reasoning_summary_part.done", {"type": "response.reasoning_summary_part.done", "output_index": index})
        elif item.get("type") == "function_call":
            yield event("response.function_call_arguments.delta", {"type": "response.function_call_arguments.delta", "item_id": item["id"], "output_index": index, "delta": item.get("arguments", "")})
            yield event("response.function_call_arguments.done", {"type": "response.function_call_arguments.done", "item_id": item["id"], "output_index": index, "arguments": item.get("arguments", "")})
        yield event("response.output_item.done", {"type": "response.output_item.done", "output_index": index, "item": item})
    terminal_type = f"response.{response['status']}"
    yield event(terminal_type, {"type": terminal_type, "response": response})
    yield b"data: [DONE]\n\n"
