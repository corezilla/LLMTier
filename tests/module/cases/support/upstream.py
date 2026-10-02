"""Programmable loopback fake upstream (ENV-3/ENV-4 transport face).

A real ThreadingHTTPServer on 127.0.0.1:0 speaking the OpenAI-compatible
protocol well enough to drive the real `OpenAIProvider` transport inside the
assembled module. Modes inject the §1.5.1 (b)/(c) upstream pathologies:
quota exhausted, non-JSON, stall/hang, slow trickle, oversized, truncated
stream, malformed frame, disconnect.
"""
from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def sse_body(events, done=True):
    blocks = "".join(f"event: {e['type']}\ndata: {json.dumps(e, ensure_ascii=False)}\n\n" for e in events)
    if done:
        blocks += "data: [DONE]\n\n"
    return blocks.encode()


def terminal_event(status="completed", output=None, usage=None, etype=None, response_extra=None):
    etype = etype or f"response.{status}"
    response = {"id": "resp_x", "object": "response", "created_at": 1, "status": status,
                "model": "backend", "output": output or [], "usage": usage,
                "error": None, "incomplete_details": None}
    if response_extra:
        response.update(response_extra)
    return {"type": etype, "response": response}


class FakeUpstream:
    """mode-driven upstream. `mode` is read per-request; counter tracks hits."""

    def __init__(self, mode="ok", chunk_delay=0.0, events=1, quota_status=429, models_mode="ok"):
        self.mode = mode
        self.models_mode = models_mode
        self.chunk_delay = chunk_delay
        self.events = events
        self.quota_status = quota_status
        self.requests = []
        self._lock = threading.Lock()
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def endpoint(self):
        return f"http://127.0.0.1:{self.port}"

    def hits(self):
        return len(self.requests)

    def stop(self):
        self._server.shutdown(); self._server.server_close()

    def _handler(self):
        outer = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def _record(self):
                with outer._lock:
                    outer.requests.append((self.command, self.path, dict(self.headers)))

            def _send(self, status, body, content_type="application/json"):
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                # Real streaming upstream: chunked transfer with small frames.
                # A single Content-Length'd multi-MB write intermittently stalls
                # on loopback (the client then trips its stream idle timeout at
                # 60s) — chunked is both the faithful SSE shape and deterministic.
                self.send_header("Transfer-Encoding", "chunked")
                self.send_header("Connection", "close")
                self.close_connection = True
                self.end_headers()
                if body:
                    try:
                        for offset in range(0, len(body), 16 * 1024):
                            piece = body[offset:offset + 16 * 1024]
                            self.wfile.write(b"%X\r\n" % len(piece) + piece + b"\r\n")
                            self.wfile.flush()
                        self.wfile.write(b"0\r\n\r\n")
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError, TimeoutError, OSError):
                        # 对端已关闭：结束本连接，不补写（handler 不得挂在 write 上）
                        self.close_connection = True

            def do_POST(self):
                outer._dispatch(self)

            def do_GET(self):
                outer._dispatch(self)

            def log_message(self, *args):
                pass

        return Handler

    def _dispatch(self, handler):
        with self._lock:
            self.requests.append((handler.command, handler.path, dict(handler.headers)))
        mode = self.mode
        if handler.path.endswith("/responses"):
            self._responses(handler, mode)
        elif handler.path.endswith("/embeddings"):
            self._embeddings(handler, mode)
        elif handler.path.endswith("/models"):
            self._models(handler)
        else:
            handler._send(404, b'{"error":{"message":"unknown path"}}')

    def _models(self, handler):
        """`GET /models` responses; `models_mode` injects catalog pathologies.

        "ok"       → a valid OpenAI-compatible `{object:list, data:[{id}]}`.
        "mixed"    → entries with missing / non-string `id`, plus a valid id
                     (the "bad data filtered, keep valid ids" stimulus).
        "non_dict" → an entry that is not an object (probes the un-filtered
                     `m.get` path).
        "error"    → upstream 503.
        """
        if self.models_mode == "error":
            handler._send(503, b'{"error":{"message":"overloaded"}}')
        elif self.models_mode == "mixed":
            body = json.dumps({"object": "list",
                               "data": [{"id": "backend"}, {"noid": 1}, {"id": 7}, {"id": "second"}]}).encode()
            handler._send(200, body)
        elif self.models_mode == "non_dict":
            body = json.dumps({"object": "list", "data": ["oops", {"id": "backend"}]}).encode()
            handler._send(200, body)
        else:
            body = json.dumps({"object": "list", "data": [{"id": "backend"}]}).encode()
            handler._send(200, body)

    def _responses(self, handler, mode):
        usage = {"input_tokens": 2, "output_tokens": 1, "total_tokens": 3}
        if mode == "ok":
            body = sse_body([terminal_event("completed", usage=usage)])
            handler._send(200, body, "text/event-stream")
        elif mode == "quota":
            handler._send(self.quota_status, json.dumps({"error": {"message": "insufficient quota"}}).encode())
        elif mode == "upstream_5xx":
            handler._send(503, b'{"error":{"message":"overloaded"}}')
        elif mode == "nonjson":
            handler._send(200, b"<html>not json</html>")
        elif mode == "stall":
            handler.send_response(200)
            handler.send_header("Content-Type", "text/event-stream")
            handler.end_headers()
            handler.wfile.write(b"")  # headers only, then hold
            time.sleep(3600)
        elif mode == "trickle":
            handler.send_response(200)
            handler.send_header("Content-Type", "text/event-stream")
            handler.send_header("Connection", "close")
            handler.end_headers()
            for i in range(self.events):
                handler.wfile.write(b"event: ping\ndata: {}\n\n")
                handler.wfile.flush()
                time.sleep(self.chunk_delay)
            time.sleep(30)
        elif mode == "oversize":
            big = "y" * (2 * 1024 * 1024)
            body = sse_body([terminal_event("completed", output=[{"type": "message", "id": "m", "role": "assistant", "status": "completed", "content": [{"type": "output_text", "text": big, "annotations": []}]}], usage=usage)])
            handler._send(200, body, "text/event-stream")
        elif mode == "many_events":
            events = [{"type": "response.output_item.added", "output_index": i, "item": {"type": "reasoning", "id": f"r{i}", "summary": []}} for i in range(self.events)]
            events.append(terminal_event("completed", usage=usage))
            handler._send(200, sse_body(events), "text/event-stream")
        elif mode == "truncated":
            body = b"event: response.created\ndata: {\"type\":\"response.created\",\"response\":{}}\n\n"
            handler._send(200, body, "text/event-stream")  # no terminal, clean EOF
        elif mode == "badframe":
            body = b"event: response.created\ndata: {not json}\n\n"
            handler._send(200, body, "text/event-stream")
        elif mode == "non_sse":
            handler._send(200, b"plain", "text/plain")
        elif mode == "close":
            handler.close_connection = True
            handler.wfile.close()
        else:
            handler._send(500, b'{"error":{"message":"bad mode"}}')

    def _embeddings(self, handler, mode):
        if mode == "embed_ok":
            handler._send(200, json.dumps({"object": "list", "data": [{"object": "embedding", "index": 0, "embedding": [0.1, 0.2]}], "model": "backend", "usage": {"prompt_tokens": 5, "total_tokens": 5}}).encode())
        elif mode == "quota":
            handler._send(self.quota_status, json.dumps({"error": {"message": "insufficient quota"}}).encode())
        elif mode == "nonjson":
            handler._send(200, b"<html>not json</html>")
        elif mode == "bad_shape":
            handler._send(200, b'{"nope": true}')
        elif mode == "badvector":
            handler._send(200, json.dumps({"object": "list", "data": [{"object": "embedding", "index": 0, "embedding": [0.1, "NaN"]}], "usage": {"prompt_tokens": 1, "total_tokens": 1}}).encode())
        else:
            handler._send(500, b'{"error":{}}')
