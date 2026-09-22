#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from datetime import datetime, timedelta, timezone


class Client:
    def __init__(self, base): self.base=base.rstrip("/"); self.admin="dev-admin"; self.data="dev-data"
    def call(self, path, method="GET", body=None, admin=True, headers=None, raw=False):
        h={"Authorization":f"Bearer {self.admin if admin else self.data}","Content-Type":"application/json",**(headers or {})}; req=urllib.request.Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,headers=h,method=method)
        try:
            with urllib.request.urlopen(req,timeout=10) as r: return (r.status,r.read() if raw else json.loads(r.read() or b"null"),dict(r.headers))
        except urllib.error.HTTPError as e: return (e.code,json.loads(e.read() or b"{}"),dict(e.headers))


def main():
    p=argparse.ArgumentParser(); p.add_argument("--base",default="http://127.0.0.1:8180"); p.add_argument("--provider",default="http://127.0.0.1:9191"); p.add_argument("--write-settings"); a=p.parse_args()
    if a.write_settings:
        Path(a.write_settings).write_text(json.dumps({"providers":[],"deployments":[],"service_levels":[]},indent=2)+"\n")
        print(a.write_settings); return
    c=Client(a.base); passed=[]
    def check(name, ok):
        if not ok: raise AssertionError(name)
        passed.append(name); print(f"PASS {len(passed):02d} {name}")
    check("health",c.call('/healthz',admin=False)[0]==200)
    s,pv,h=c.call('/v1/providers','POST',{'name':'Synthetic Local','kind':'local','endpoint':a.provider.rstrip('/')+'/v1','secret_ref':None,'enabled':True}); check("provider CRUD create",s==201 and pv['kind']=='local')
    capabilities={'responses':True,'embeddings':False,'tools':True,'structured_outputs':False,'input_modalities':['text'],'output_modalities':['text'],'context_window':128000,'max_output_tokens':16384,'embedding_space_id':None,'embedding_dimensions':None,'embedding_max_batch_inputs':None,'embedding_max_input_tokens':None}
    s,dv,_=c.call('/v1/deployments','POST',{'name':'Synthetic Responses','provider_id':pv['id'],'backend_model':'synthetic-chat','capabilities':capabilities,'enabled':True}); check("deployment CRUD create",s==201)
    ep=dict(capabilities); ep.update(responses=False,embeddings=True,tools=False,output_modalities=['embedding'],context_window=None,max_output_tokens=None,embedding_space_id='bge-m3-dense-1024-v1',embedding_dimensions=[1024],embedding_max_batch_inputs=32,embedding_max_input_tokens=8192)
    s,ev,_=c.call('/v1/deployments','POST',{'name':'Synthetic Embeddings','provider_id':pv['id'],'backend_model':'BAAI/bge-m3','capabilities':ep,'enabled':True}); check("embedding deployment",s==201)
    for tier,did in [('Worker',dv['id']),('Embedding-v1',ev['id'])]:
        s,t,h=c.call('/v1/service-levels/'+tier); etag=h.get('ETag'); s,t,_=c.call('/v1/service-levels/'+tier,'PATCH',{'deployment_ids':[did]},headers={'If-Match':etag}); check(f"attach {tier}",s==200)
    probe_results=[c.call('/v1/probes','POST',{'deployment_id':did,'confirm_external_call':True})[1]['status'] for did in (dv['id'],ev['id'])]
    check("model list",any(x['id']=='Worker' for x in c.call('/v1/models',admin=False)[1]['data']))
    req={'model':'Worker','input':'hello','stream':True,'store':False}; s,raw,_=c.call('/v1/responses','POST',req,admin=False,raw=True); check("Responses SSE",s==200 and b'response.completed' in raw and b'[DONE]' in raw)
    req.update(input='REFUSE'); s,raw,_=c.call('/v1/responses','POST',req,admin=False,raw=True); check("standard refusal SSE",b'response.refusal.delta' in raw)
    req.update(input='CALL_TOOL',tools=[{'type':'function','name':'clock','description':'clock','parameters':{'type':'object','properties':{}}}]); s,raw,_=c.call('/v1/responses','POST',req,admin=False,raw=True); check("tool call SSE",b'function_call_arguments.delta' in raw)
    s,e,_=c.call('/v1/embeddings','POST',{'model':'Embedding-v1','input':['a','b'],'dimensions':1024,'encoding_format':'float'},admin=False); check("float embeddings",s==200 and len(e['data'])==2 and len(e['data'][0]['embedding'])==1024)
    s,e,_=c.call('/v1/embeddings','POST',{'model':'Embedding-v1','input':'a','dimensions':1024,'encoding_format':'base64'},admin=False); check("base64 embeddings",s==200 and isinstance(e['data'][0]['embedding'],str))
    to=datetime.now(timezone.utc).isoformat().replace('+00:00','Z'); start=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat().replace('+00:00','Z'); window='from='+urllib.parse.quote(start)+'&to='+urllib.parse.quote(to)
    u=c.call('/v1/usage?'+window,admin=False)[1]; check("principal usage measured",len(u['data'])>=5 and all('measurement_status' in x for x in u['data']))
    snap=u['snapshot_id']; check("stable usage snapshot",c.call('/v1/usage?'+window+'&cursor='+snap+':0',admin=False)[1]['snapshot_id']==snap)
    check("admin ETag conflict",c.call('/v1/providers/'+pv['id'],'PATCH',{'enabled':False},headers={'If-Match':'"wrong"'})[0]==412)
    s,_,_=c.call('/v1/service-levels/Worker','DELETE',headers={'If-Match':'"Worker.v2"'}); check("fixed Tier cannot delete",s==409)
    check("audit and logs",len(c.call('/v1/audit')[1]['data'])>0 and len(c.call('/v1/logs?'+window)[1]['data'])>0)
    check("probe and readiness",probe_results==['healthy','healthy'])
    req=urllib.request.Request(a.base+'/ui/app.js'); check("Web UI assets",urllib.request.urlopen(req).status==200)
    print(f"RESULT {len(passed)}/{len(passed)} synthetic debug scenarios passed")


if __name__=='__main__': main()
