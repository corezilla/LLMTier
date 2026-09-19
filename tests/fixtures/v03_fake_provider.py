#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import struct
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass
    def reply(self, status, data):
        raw=json.dumps(data,separators=(",", ":")).encode(); self.send_response(status); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(raw))); self.send_header("X-Request-ID",f"fake_{uuid.uuid4().hex[:8]}"); self.end_headers(); self.wfile.write(raw)
    def reply_sse(self, response):
        event={"type":"response.completed","sequence_number":0,"response":response}; raw=("event: response.completed\ndata: "+json.dumps(event,separators=(",", ":"))+"\n\ndata: [DONE]\n\n").encode()
        self.send_response(200); self.send_header("Content-Type","text/event-stream"); self.send_header("Content-Length",str(len(raw))); self.send_header("X-Request-ID",f"fake_{uuid.uuid4().hex[:8]}"); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        if self.path == "/healthz": self.reply(200,{"status":"ok"})
        elif self.path == "/v1/models": self.reply(200,{"object":"list","data":[{"id":"synthetic-chat","object":"model"},{"id":"BAAI/bge-m3","object":"model"}]})
        else: self.reply(404,{"error":"not found"})
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers.get("Content-Length","0"))) or b"{}")
        delay = int(body.get("metadata", {}).get("synthetic_delay_ms", "0")) if isinstance(body.get("metadata"), dict) else 0
        if delay: time.sleep(min(delay, 35000) / 1000)
        if body.get("model")=="force-503": return self.reply(503,{"error":{"message":"synthetic failure"}})
        if self.path=="/v1/responses":
            prompt=json.dumps(body.get("input"),ensure_ascii=False); inp=max(1,len(prompt)//4)
            if "REFUSE" in prompt: content=[{"type":"refusal","refusal":"Cannot comply with synthetic request"}]
            elif body.get("tools") and "CALL_TOOL" in prompt: content=None
            else: content=[{"type":"output_text","text":"Synthetic provider response","annotations":[]}]
            output=([{"id":"fc_fake","type":"function_call","call_id":"call_01","name":body["tools"][0]["name"],"arguments":"{}","status":"completed"}] if content is None else [{"id":"msg_fake","type":"message","role":"assistant","status":"completed","content":content}])
            response={"id":"resp_upstream","object":"response","created_at":int(time.time()),"status":"completed","model":body["model"],"output":output,"usage":{"input_tokens":inp,"output_tokens":4,"total_tokens":inp+4,"input_tokens_details":{"cached_tokens":0,"cache_write_tokens":0},"output_tokens_details":{"reasoning_tokens":0}},"error":None}
            return self.reply_sse(response) if body.get("stream") is True else self.reply(400,{"error":{"message":"stream=true required"}})
        if self.path=="/v1/embeddings":
            inputs=body.get("input"); inputs=[inputs] if isinstance(inputs,str) else inputs; dim=body.get("dimensions",8); fmt=body.get("encoding_format","float"); data=[]
            for i,text in enumerate(inputs):
                seed=hashlib.sha256(text.encode()).digest(); vec=[((seed[j%len(seed)]/255)*2-1) for j in range(dim)]; norm=math.sqrt(sum(x*x for x in vec)) or 1; vec=[x/norm for x in vec]
                emb=base64.b64encode(struct.pack("<"+"f"*len(vec),*vec)).decode() if fmt=="base64" else vec
                data.append({"object":"embedding","index":i,"embedding":emb})
            tokens=sum(max(1,len(x)//4) for x in inputs); return self.reply(200,{"object":"list","data":data,"model":body["model"],"usage":{"prompt_tokens":tokens,"total_tokens":tokens}})
        self.reply(404,{"error":"not found"})


if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--host",default="127.0.0.1"); p.add_argument("--port",type=int,default=9191); a=p.parse_args(); print(f"fake provider http://{a.host}:{a.port}",flush=True); ThreadingHTTPServer((a.host,a.port),Handler).serve_forever()
