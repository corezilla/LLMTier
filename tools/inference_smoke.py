#!/usr/bin/env python3
"""LLMTier Inference (Data Plane) smoke test.

Exercises the two consumer APIs end to end:
  - POST /v1/responses  (stream=true, store=false) -> standard SSE
  - POST /v1/embeddings (encoding_format=float | base64)
plus GET /healthz and GET /readyz.

Per testing-standard TS-003 this targets a LAN service by default
(http://192.168.1.9:8181 = m5air). A fake upstream is available for local runs:
  PYTHONPATH=src python3 tests/fixtures/v03_fake_provider.py --port 9191
  PYTHONPATH=src python3 -m http_api --host 0.0.0.0 --port 8181 \
      --database /tmp/lt.sqlite3 --settings /tmp/settings.json   # provider endpoint = LAN IP

Auth: data credential (`--data-token`, default env LLMTIER_DATA_TOKEN / 'dev-data').
Exit code: 0 if all checks pass, 1 otherwise.

Dependencies: a reachable LLMTier with a responses-capable tier (--model, default 'Worker').
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request


def http(base, path, token, *, method="GET", body=None, timeout=60):
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(base.rstrip("/") + path, data=data, headers=headers, method=method)
    return urllib.request.urlopen(req, timeout=timeout)


def json_call(base, path, token, **kw):
    try:
        with http(base, path, token, **kw) as response:
            raw = response.read()
            return response.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return exc.code, json.loads(raw) if raw else None
        except json.JSONDecodeError:
            return exc.code, {"raw": raw[:200].decode("utf-8", "replace")}


class Result:
    def __init__(self):
        self.checks = []

    def check(self, name, ok, detail=""):
        self.checks.append((name, bool(ok), detail))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
        return ok

    @property
    def ok(self):
        return all(ok for _, ok, _ in self.checks)


def sse_events(base, token, body):
    """Stream POST /v1/responses and yield the ordered event names + payloads."""
    events, terminal, seen_done, text = [], None, False, []
    with http(base, "/v1/responses", token, method="POST", body=body) as response:
        buffer = ""
        for chunk in iter(lambda: response.read(1), b""):
            buffer += chunk.decode("utf-8", "ignore")
            while "\n\n" in buffer:
                block, buffer = buffer.split("\n\n", 1)
                name = data = None
                for line in block.splitlines():
                    if line.startswith("event: "):
                        name = line[7:].strip()
                    elif line.startswith("data: "):
                        data = line[6:].strip()
                if data == "[DONE]":
                    seen_done = True
                    continue
                if name and name != "error":
                    events.append(name)
                if data and data != "[DONE]":
                    try:
                        payload = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    kind = payload.get("type", name)
                    if kind in {"response.completed", "response.incomplete", "response.failed"}:
                        terminal = terminal or payload
                    if kind == "response.output_text.delta":
                        text.append(payload.get("delta", ""))
    return events, terminal, seen_done, "".join(text)


def run(args):
    result = Result()
    base, token, model = args.base, args.data_token, args.model
    print(f"LLMTier inference smoke → {base} (model={model})")

    print("\n[1] health / readiness")
    status, body = json_call(base, "/healthz", None)
    result.check("GET /healthz 200", status == 200, f"status={status} body={body}")

    print("\n[2] POST /v1/responses (SSE)")
    started = time.monotonic()
    try:
        events, terminal, seen_done, text = sse_events(base, token, {
            "model": model,
            "input": [{"role": "user", "content": "Reply with the single word: pong"}],
            "stream": True,
            "store": False,
            "max_output_tokens": 32,
        })
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        result.check("POST /v1/responses 2xx", False, f"status={exc.code} body={raw[:200]!r}")
        return result
    elapsed = (time.monotonic() - started) * 1000
    result.check("stream opened (HTTP 200)", True, f"{elapsed:.0f} ms")
    result.check("event response.created", "response.created" in events)
    result.check(">=1 output_text.delta", bool(text), f"text={text[:40]!r}")
    result.check("exactly one terminal", terminal is not None, f"terminal={terminal.get('type') if terminal else None}")
    result.check("SEE [DONE]", seen_done)
    if terminal:
        usage = terminal.get("response", {}).get("usage")
        result.check("terminal usage field", "usage" in terminal.get("response", {}), f"usage={usage}")

    print("\n[3] POST /v1/embeddings")
    for encoding in ("float", "base64"):
        status, body = json_call(base, "/v1/embeddings", token, method="POST", body={
            "model": args.embedding_model,
            "input": ["alpha", "beta"],
            "encoding_format": encoding,
        })
        if status != 200:
            result.check(f"embeddings[{encoding}] 200", False, f"status={status} body={body}")
            continue
        data = (body or {}).get("data", [])
        result.check(f"embeddings[{encoding}] object=list", (body or {}).get("object") == "list")
        result.check(f"embeddings[{encoding}] 2 vectors", len(data) == 2, f"len={len(data)}")
        first = data[0].get("embedding") if data else None
        result.check(f"embeddings[{encoding}] vector present", bool(first))

    print(f"\n{'OK' if result.ok else 'FAILED'}: {sum(1 for _, ok, _ in result.checks if ok)}/{len(result.checks)} checks passed")
    return result


def main():
    parser = argparse.ArgumentParser(description="LLMTier inference (Data Plane) smoke test")
    parser.add_argument("--base", default=os.environ.get("LLMTIER_BASE", "http://192.168.1.9:8181"),
                        help="LLMTier base URL (TS-003: LAN service)")
    parser.add_argument("--data-token", default=os.environ.get("LLMTIER_DATA_TOKEN", "dev-data"))
    parser.add_argument("--model", default=os.environ.get("LLMTIER_MODEL", "Worker"), help="responses-capable tier")
    parser.add_argument("--embedding-model", default=os.environ.get("LLMTIER_EMBEDDING_MODEL", "Embedding-v1"))
    args = parser.parse_args()
    sys.exit(0 if run(args).ok else 1)


if __name__ == "__main__":
    main()
