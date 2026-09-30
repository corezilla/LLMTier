#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import struct
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


# Slow-embeddings gate: cleared by default (closed). Requests to
# /v1/embeddings with model == "slow-embeddings" block until the test releases
# the gate (GET /control/release) or the bounded timeout elapses. This lets a
# system test hold the sole deployment concurrency slot deterministically while
# keeping teardown clean (release drains every blocked request immediately).
_GATE = threading.Event()
_GATE_TIMEOUT_S = 30.0


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass
    def reply(self, status, data):
        raw=json.dumps(data,separators=(",", ":")).encode(); self.send_response(status); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(raw))); self.send_header("X-Request-ID",f"fake_{uuid.uuid4().hex[:8]}"); self.end_headers(); self.wfile.write(raw)
    def reply_sse(self, response, stream_body=None, content_type="text/event-stream", status=200):
        if stream_body is None:
            event={"type":"response.completed","sequence_number":0,"response":response}; stream_body="event: response.completed\ndata: "+json.dumps(event,separators=(",", ":"))+"\n\ndata: [DONE]\n\n"
        raw=stream_body.encode()
        self.send_response(status); self.send_header("Content-Type",content_type); self.send_header("Content-Length",str(len(raw))); self.send_header("X-Request-ID",f"fake_{uuid.uuid4().hex[:8]}"); self.end_headers(); self.wfile.write(raw)
    def reply_responses_contract(self, model, response):
        """Emit a Responses SSE that violates the terminal contract for DP-RESP-25."""
        def frame(name, response_obj):
            ev={"type":name,"sequence_number":0,"response":response_obj}
            return f"event: {name}\ndata: "+json.dumps(ev,separators=(",", ":"))+"\n\n"
        created=dict(response); created["status"]="in_progress"; created["output"]=[]; created["usage"]=None
        if model=="force-non-sse":
            return self.reply_sse(response, stream_body=json.dumps({"object":"response","status":"completed"}), content_type="application/json")
        if model=="force-two-terminals":
            return self.reply_sse(response, stream_body=frame("response.created", created)+frame("response.completed", response)+frame("response.completed", response)+"data: [DONE]\n\n")
        if model=="force-no-terminal":
            return self.reply_sse(response, stream_body=frame("response.created", created)+"data: [DONE]\n\n")
        if model=="force-status-mismatch":
            bad=dict(response); bad["status"]="failed"
            return self.reply_sse(response, stream_body=frame("response.created", created)+frame("response.completed", bad)+"data: [DONE]\n\n")
        return self.reply_sse(response)
    def do_GET(self):
        if self.path == "/healthz": self.reply(200,{"status":"ok"})
        elif self.path == "/control/release": _GATE.set(); self.reply(200,{"gate":"released"})
        elif self.path == "/control/reset": _GATE.clear(); self.reply(200,{"gate":"closed"})
        elif self.path == "/v1/models": self.reply(200,{"object":"list","data":[{"id":"synthetic-chat","object":"model"},{"id":"BAAI/bge-m3","object":"model"}]})
        else: self.reply(404,{"error":"not found"})
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers.get("Content-Length","0"))) or b"{}")
        delay = int(body.get("metadata", {}).get("synthetic_delay_ms", "0")) if isinstance(body.get("metadata"), dict) else 0
        if delay: time.sleep(min(delay, 35000) / 1000)
        if body.get("model")=="force-503": return self.reply(503,{"error":{"message":"synthetic failure"}})
        if body.get("model")=="slow-embeddings": _GATE.wait(_GATE_TIMEOUT_S)
        # Deterministic slot holder for DP-RESP-20: blocks until the gate is
        # released (/control/release) or the bounded timeout elapses, so the B
        # instance's sole admission slot is held without a long sleep leaking
        # past teardown.
        if body.get("model")=="slow-responses": _GATE.wait(_GATE_TIMEOUT_S)
        if self.path=="/v1/responses":
            model=body.get("model")
            # DP-RESP-23: real upstream non-success HTTP (no injection).
            if model in {"force-http-422","force-http-429","force-http-500"}:
                code=int(model.rsplit("-",1)[1])
                return self.reply(code,{"error":{"message":f"synthetic upstream {code}"}})
            prompt=json.dumps(body.get("input"),ensure_ascii=False); inp=max(1,len(prompt)//4)
            if model in {"force-long-stream", "force-huge-stream"}:
                # Many delta events so a mid-stream client disconnect reliably
                # surfaces as BrokenPipeError at the gateway (DP-RESP-21).
                # force-huge-stream is deliberately far larger than any socket
                # buffer, making the server-side write block after the client
                # closes -> a deterministic (non-racy) aborted trace.
                n = 20000 if model == "force-huge-stream" else 500
                content=[{"type":"output_text","text":f"chunk-{i} ","annotations":[]} for i in range(n)]
                output=[{"id":"msg_long","type":"message","role":"assistant","status":"completed","content":content}]
                response={"id":"resp_upstream","object":"response","created_at":int(time.time()),"status":"completed","model":model,"output":output,"usage":{"input_tokens":inp,"output_tokens":n,"total_tokens":inp+n,"input_tokens_details":{"cached_tokens":0,"cache_write_tokens":0},"output_tokens_details":{"reasoning_tokens":0}},"error":None}
                return self.reply_sse(response)
            if model in {"force-non-sse","force-two-terminals","force-no-terminal","force-status-mismatch"}:
                output=[{"id":"msg_fake","type":"message","role":"assistant","status":"completed","content":[{"type":"output_text","text":"Synthetic provider response","annotations":[]}]}]
                response={"id":"resp_upstream","object":"response","created_at":int(time.time()),"status":"completed","model":model,"output":output,"usage":{"input_tokens":inp,"output_tokens":4,"total_tokens":inp+4,"input_tokens_details":{"cached_tokens":0,"cache_write_tokens":0},"output_tokens_details":{"reasoning_tokens":0}},"error":None}
                return self.reply_responses_contract(model, response)
            if "REFUSE" in prompt: content=[{"type":"refusal","refusal":"Cannot comply with synthetic request"}]
            elif body.get("tools") and "CALL_TOOL" in prompt: content=None
            else: content=[{"type":"output_text","text":"Synthetic provider response","annotations":[]}]
            output=([{"id":"fc_fake","type":"function_call","call_id":"call_01","name":body["tools"][0]["name"],"arguments":"{}","status":"completed"}] if content is None else [{"id":"msg_fake","type":"message","role":"assistant","status":"completed","content":content}])
            response={"id":"resp_upstream","object":"response","created_at":int(time.time()),"status":"completed","model":body["model"],"output":output,"usage":{"input_tokens":inp,"output_tokens":4,"total_tokens":inp+4,"input_tokens_details":{"cached_tokens":0,"cache_write_tokens":0},"output_tokens_details":{"reasoning_tokens":0}},"error":None}
            return self.reply_sse(response) if body.get("stream") is True else self.reply(400,{"error":{"message":"stream=true required"}})
        if self.path=="/v1/embeddings":
            # DP-EMB-09: distinct upstream contract violations, one per model.
            if body.get("model")=="force-bad-contract": return self.reply(200,{"object":"wrong","data":[]})
            if body.get("model")=="force-bad-object": return self.reply(200,{"object":"wrong","data":[{"object":"embedding","index":0,"embedding":[0.0]}]})
            if body.get("model")=="force-non-array-data": return self.reply(200,{"object":"list","data":{"not":"an array"}})
            if body.get("model")=="force-bad-vector": return self.reply(200,{"object":"list","data":[{"object":"embedding","index":0}]})
            if body.get("model")=="force-bad-base64": return self.reply(200,{"object":"list","data":[{"object":"embedding","index":0,"embedding":"@@@not-base64@@@"}]})
            # DP-EMB-10: transport failure (drop the connection, no HTTP response).
            if body.get("model")=="force-drop":
                self.close_connection = True
                try: self.connection.shutdown(2)
                except OSError: pass
                self.connection.close()
                return
            inputs=body.get("input"); inputs=[inputs] if isinstance(inputs,str) else inputs; dim=body.get("dimensions",8); fmt=body.get("encoding_format","float"); data=[]
            for i,text in enumerate(inputs):
                seed=hashlib.sha256(text.encode()).digest(); vec=[((seed[j%len(seed)]/255)*2-1) for j in range(dim)]; norm=math.sqrt(sum(x*x for x in vec)) or 1; vec=[x/norm for x in vec]
                emb=base64.b64encode(struct.pack("<"+"f"*len(vec),*vec)).decode() if fmt=="base64" else vec
                data.append({"object":"embedding","index":i,"embedding":emb})
            tokens=sum(max(1,len(x)//4) for x in inputs); return self.reply(200,{"object":"list","data":data,"model":body["model"],"usage":{"prompt_tokens":tokens,"total_tokens":tokens}})
        self.reply(404,{"error":"not found"})


if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--host",default="127.0.0.1"); p.add_argument("--port",type=int,default=9191); a=p.parse_args(); print(f"fake provider http://{a.host}:{a.port}",flush=True); ThreadingHTTPServer((a.host,a.port),Handler).serve_forever()
