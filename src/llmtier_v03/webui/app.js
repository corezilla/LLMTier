const $=selector=>document.querySelector(selector);
const $$=selector=>[...document.querySelectorAll(selector)];

async function api(path,{method='GET',body,headers={}}={}){
  const response=await fetch(path,{method,credentials:'same-origin',headers:{'Content-Type':'application/json',...headers},body:body?JSON.stringify(body):undefined});
  if(!response.ok){let error={};try{error=await response.json()}catch{}throw new Error(error.error?.message||`${response.status} ${response.statusText}`)}
  return response.status===204?null:response.json();
}

const esc=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const etag=item=>`"${item.id}.v${item.version}"`;
const windowQuery=()=>{const to=new Date(),from=new Date(to.getTime()-7*86400000);return `from=${encodeURIComponent(from.toISOString())}&to=${encodeURIComponent(to.toISOString())}`};
const caps=kind=>({responses:kind==='responses',embeddings:kind==='embeddings',tools:kind==='responses',structured_outputs:false,input_modalities:['text'],output_modalities:kind==='embeddings'?['embedding']:['text'],context_window:kind==='responses'?128000:null,max_output_tokens:kind==='responses'?16384:null,embedding_space_id:kind==='embeddings'?'bge-m3-dense-1024-v1':null,embedding_dimensions:kind==='embeddings'?[1024]:null,embedding_max_batch_inputs:kind==='embeddings'?32:null,embedding_max_input_tokens:kind==='embeddings'?8192:null});

let state={providers:[],deployments:[],tiers:[],runtime:{deployments:{},queues:{}},usage:[]};
let editingTierId=null;

const iconSvg=name=>`<svg viewBox="0 0 24 24" aria-hidden="true"><use href="/ui/icons.svg#icon-${esc(name)}"></use></svg>`;
const statusIconName=label=>({Running:'activity',Ready:'circle-check',measured:'circle-check',Idle:'circle-dot',Paused:'circle-pause',Probing:'scan-search',Exhausted:'gauge',Attention:'triangle-alert',Degraded:'triangle-alert',Unreachable:'cloud-off','Not ready':'triangle-alert','Connection failed':'cloud-off',Disabled:'circle-off',Empty:'package-open'}[label]||'circle-help');
const statusMarkup=(label,tone='muted')=>`<span class="status-icon ${tone}" role="img" tabindex="0" title="${esc(label)}" aria-label="${esc(label)}">${iconSvg(statusIconName(label))}</span>`;
const iconButton=(name,label,className,data='')=>`<button type="button" class="icon-action ${className}" ${data} title="${esc(label)}" aria-label="${esc(label)}">${iconSvg(name)}</button>`;
const metric=value=>value==null?'<span class="unknown">Unknown</span>':`<span class="metric">${esc(value)}</span>`;

function backendState(deployment,provider,runtime={}){
  if(!provider?.enabled)return ['Disabled','muted'];
  if(!deployment.enabled)return ['Paused','muted'];
  const value=String(deployment.health||'unknown').toLowerCase();
  if(value==='healthy'||value==='running')return [(runtime.running||0)>0?'Running':'Idle','ok'];
  if(value==='probing')return ['Probing','warn'];
  if(value==='exhausted')return ['Exhausted','warn'];
  if(value==='unhealthy'||value==='unreachable')return ['Unreachable','bad'];
  return ['Unknown','muted'];
}
function tierState(tier,deployments){
  if(!tier.enabled)return ['Disabled','muted'];
  if(!deployments.length)return ['Empty','muted'];
  const states=deployments.map(deployment=>backendState(deployment,state.providers.find(item=>item.id===deployment.provider_id),state.runtime.deployments[deployment.id])[0]);
  if(states.includes('Running'))return ['Running','ok'];
  if(states.includes('Idle'))return ['Idle','ok'];
  for(const name of ['Probing','Exhausted','Unreachable'])if(states.includes(name))return [name,name==='Unreachable'?'bad':'warn'];
  if(states.includes('Paused')&&states.every(name=>name==='Paused'||name==='Disabled'))return ['Paused','muted'];
  if(states.every(name=>name==='Disabled'))return ['Disabled','muted'];
  return ['Unknown','muted'];
}
function providerOptions(selected){return state.providers.map(provider=>`<option value="${esc(provider.id)}" ${provider.id===selected?'selected':''}>${esc(provider.name)} · ${esc(provider.kind)}</option>`).join('')}

async function loadRegistry(){
  const [providers,deployments,tiers,runtime]=await Promise.all([api('/tier/admin/v1/providers'),api('/tier/admin/v1/deployments'),api('/tier/admin/v1/service-levels'),api('/tier/admin/v1/runtime')]);
  state={...state,providers:providers.data,deployments:deployments.data,tiers:tiers.data,runtime};
}

async function loadUsageSnapshot(){
  const page=await api('/tier/admin/v1/usage?'+windowQuery()+'&limit=100');
  state.usage=page.data;
  return page;
}

async function loadHome(){
  try{
    const readyPromise=fetch('/readyz',{credentials:'same-origin'}).then(async response=>({ok:response.ok,...await response.json()}));
    const healthPromise=api('/healthz');
    const [,usagePage]=await Promise.all([loadRegistry(),loadUsageSnapshot()]);
    const [ready,health]=await Promise.all([readyPromise,healthPromise]);
    const gateway=ready.status==='ready'?'Ready':ready.status==='degraded'?'Degraded':'Not ready';
    $('#gateway').className=`status-chip ${ready.status==='ready'?'ok':ready.status==='degraded'?'warn':'bad'}`;
    $('#gateway').innerHTML=statusMarkup(gateway,ready.status==='ready'?'ok':ready.status==='degraded'?'warn':'bad');
    $('#gateway').title=gateway;$('#gateway').setAttribute('aria-label',gateway);
    const running=Object.values(state.runtime.deployments).reduce((sum,item)=>sum+item.running,0);
    const maximum=Object.values(state.runtime.deployments).reduce((sum,item)=>sum+item.max_concurrent,0);
    const available=(ready.models||[]).filter(item=>item.availability==='available').length;
    const activeModels=state.deployments.filter(item=>['Idle','Running'].includes(backendState(item,state.providers.find(provider=>provider.id===item.provider_id),state.runtime.deployments[item.id])[0])).length;
    $('#tier-summary').textContent=`Tiers ${available}/${state.tiers.length}`;
    $('#model-summary').textContent=`Models ${activeModels}/${state.deployments.length}`;
    $('#load-summary').textContent=`Load ${running}/${maximum}${usagePage.has_more?' · Usage 100+':''}`;
    $('#build-meta').textContent=`Version ${health.version} · Updated ${new Date(document.lastModified).toLocaleString()}`;
    renderTree();
    $('#stamp').textContent=`Last refreshed ${new Date().toLocaleTimeString()}`;
  }catch(error){$('#tree').textContent=error.message;$('#gateway').innerHTML=statusMarkup('Connection failed','bad');$('#gateway').title='Connection failed';$('#gateway').setAttribute('aria-label','Connection failed');$('#gateway').className='status-chip bad'}
}

function renderTree(){
  const provider=id=>state.providers.find(item=>item.id===id);
  $('#tree').className='tree';
  $('#tree').innerHTML=state.tiers.map(tier=>{
    const deployments=tier.deployment_ids.map(id=>state.deployments.find(item=>item.id===id)).filter(Boolean);
    const overall=tierState(tier,deployments);
    const tierRuntime=deployments.reduce((sum,item)=>{const current=state.runtime.deployments[item.id]||{};sum.running+=current.running||0;sum.max+=current.max_concurrent||0;return sum},{running:0,max:0});
    const usage=state.usage.filter(item=>item.model===tier.id);
    const tierTokens=usage.some(item=>item.total_tokens==null)?null:usage.reduce((sum,item)=>sum+item.total_tokens,0);
    const rows=deployments.map(deployment=>{
      const runtime=state.runtime.deployments[deployment.id]||{};
      const owner=provider(deployment.provider_id),status=backendState(deployment,owner,runtime);
      const toggleName=deployment.enabled?'pause':'play',toggleLabel=deployment.enabled?'Pause model':'Resume model';
      return `<div class="backend"><span>└ <b>${esc(deployment.name)}</b><div class="subline">${esc(deployment.backend_model)} · v${deployment.version}</div></span><span>${statusMarkup(status[0],status[1])}</span><span>${metric(`${runtime.running??0} / ${runtime.max_concurrent??'?'}`)}</span><span class="unknown" title="Usage is recorded by Tier; the selected backend is not persisted">—</span><span>${esc(owner?.name||'Unknown provider')}</span><span>${owner?.kind==='cloud'?'Cloud':'Local'}</span><span class="backend-actions">${iconButton(toggleName,toggleLabel,'backend-toggle',`data-deployment="${esc(deployment.id)}"`)}${iconButton('refresh-cw','Probe backend','backend-probe',`data-deployment="${esc(deployment.id)}" ${status[0]==='Disabled'||status[0]==='Paused'?'disabled':''}`)}</span></div>`;
    }).join('');
    return `<details open><summary><span class="tiername"><b>${esc(tier.id)}</b><div class="subline">${deployments.length} members · v${tier.version}</div></span><span>${statusMarkup(overall[0],overall[1])}</span><span>${metric(`${tierRuntime.running} / ${tierRuntime.max}`)}</span><span>${metric(usage.length?`${usage.length} calls · ${tierTokens??'Unknown'} tok`:'No calls')}</span><span>—</span><span></span><span>${iconButton('pencil',`Edit ${tier.id}`,'tier-edit',`data-tier="${esc(tier.id)}"`)}</span></summary>${rows}</details>`;
  }).join('')||'<div class="empty">No tiers configured</div>';
  $$('#tree .tier-edit').forEach(button=>button.onclick=event=>{event.preventDefault();event.stopPropagation();openTierEditor(button.dataset.tier)});
  $$('#tree .backend-toggle').forEach(button=>button.onclick=()=>toggleDeployment(button));
  $$('#tree .backend-probe').forEach(button=>button.onclick=()=>probeDeployment(button));
}

async function toggleDeployment(button){
  const deployment=state.deployments.find(item=>item.id===button.dataset.deployment);if(!deployment)return;
  const runtime=state.runtime.deployments[deployment.id]||{};
  if(deployment.enabled&&(runtime.running||0)>0&&!window.confirm('Pause this model? New requests will stop, but active requests will continue.'))return;
  button.disabled=true;
  try{await api(`/tier/admin/v1/deployments/${encodeURIComponent(deployment.id)}`,{method:'PATCH',headers:{'If-Match':etag(deployment)},body:{enabled:!deployment.enabled}});await loadHome()}
  catch(error){window.alert(`${deployment.enabled?'Pause':'Resume'} failed: ${error.message}`);button.disabled=false}
}

async function probeDeployment(button){
  const deploymentId=button.dataset.deployment;if(!deploymentId)return;
  if(!window.confirm('Probe this backend now? This makes one provider request.'))return;
  button.disabled=true;button.textContent='…';
  try{await api('/tier/admin/v1/probes',{method:'POST',body:{deployment_id:deploymentId,confirm_external_call:true}});await loadHome()}
  catch(error){window.alert(`Probe failed: ${error.message}`);button.disabled=false;button.innerHTML=iconSvg('refresh-cw')}
}

async function loadProviders(){
  try{await Promise.all([loadRegistry(),loadUsageSnapshot()]);renderProviders()}catch(error){$('#provider-error').textContent=error.message}
}

function renderProviders(){
  $('#provider-body').innerHTML=state.providers.map(provider=>{
    const deployments=state.deployments.filter(item=>item.provider_id===provider.id);
    const load=deployments.reduce((sum,item)=>{const current=state.runtime.deployments[item.id]||{};sum.running+=current.running||0;sum.max+=current.max_concurrent||0;return sum},{running:0,max:0});
    const available=provider.enabled&&deployments.some(item=>['Idle','Running'].includes(backendState(item,provider,state.runtime.deployments[item.id])[0]));
    const providerStatus=!provider.enabled?'Disabled':load.running>0?'Running':available?'Idle':'Attention';
    return `<tr><td><b>${esc(provider.name)}</b><div class="subline">${esc(provider.id)}</div></td><td>${provider.kind==='cloud'?'Cloud':'Local'}</td><td>${esc(provider.endpoint)}</td><td>${provider.has_secret?'Configured':'None'}</td><td>${statusMarkup(providerStatus,providerStatus==='Running'||providerStatus==='Idle'?'ok':providerStatus==='Attention'?'warn':'muted')}</td><td>${metric(null)}</td><td><span class="unknown" title="Current usage records identify Tier, not provider account">Unknown</span></td><td>${metric(`${load.running} / ${load.max}`)}</td><td class="row-actions">${iconButton('pencil','Edit provider','provider-edit',`data-provider="${esc(provider.id)}"`)}${iconButton('trash-2','Delete provider','provider-delete danger',`data-provider="${esc(provider.id)}"`)}</td></tr>`;
  }).join('')||'<tr><td colspan="9">No providers configured</td></tr>';
  $$('.provider-edit').forEach(button=>button.onclick=()=>openProviderEditor(button.dataset.provider));
  $$('.provider-delete').forEach(button=>button.onclick=()=>deleteProvider(button.dataset.provider));
}

function openProviderEditor(id=null){
  const provider=state.providers.find(item=>item.id===id);
  const form=$('#provider-form');form.reset();
  form.elements.provider_id.value=provider?.id||'';
  form.elements.provider_version.value=provider?.version||'';
  form.elements.name.value=provider?.name||'';
  form.elements.kind.value=provider?.kind||'cloud';
  form.elements.endpoint.value=provider?.endpoint||'';
  form.elements.secret_ref.value='';
  form.elements.enabled.checked=provider?.enabled??true;
  $('#provider-drawer-title').textContent=provider?'Edit Provider':'Add Provider';
  $('#provider-secret-help').textContent=provider&&provider.has_secret?'API key configured. Leave blank to keep it.':'Use an env: or file: API key reference; never paste the key value.';
  $('#provider-form-error').textContent='';
  $('#provider-mask').classList.add('open');
}

async function saveProvider(event){
  event.preventDefault();
  const form=event.currentTarget,id=form.elements.provider_id.value;
  const body={name:form.elements.name.value,kind:form.elements.kind.value,endpoint:form.elements.endpoint.value,enabled:form.elements.enabled.checked};
  if(form.elements.secret_ref.value)body.secret_ref=form.elements.secret_ref.value;
  try{
    if(id)await api(`/tier/admin/v1/providers/${encodeURIComponent(id)}`,{method:'PATCH',headers:{'If-Match':`"${id}.v${form.elements.provider_version.value}"`},body});
    else await api('/tier/admin/v1/providers',{method:'POST',body:{...body,secret_ref:form.elements.secret_ref.value||null}});
    $('#provider-mask').classList.remove('open');await loadProviders();
  }catch(error){$('#provider-form-error').textContent=error.message}
}

async function deleteProvider(id){
  const provider=state.providers.find(item=>item.id===id);if(!provider)return;
  if(!window.confirm(`Delete provider “${provider.name}”?`))return;
  try{await api(`/tier/admin/v1/providers/${encodeURIComponent(id)}`,{method:'DELETE',headers:{'If-Match':etag(provider)}});await loadProviders()}
  catch(error){$('#provider-error').textContent=error.message}
}

function openTierEditor(id){
  editingTierId=id;
  $('#tier-drawer-title').textContent=`Edit ${id}`;
  $('#tier-form-error').textContent='';
  renderTierMembers();
  $('#tier-mask').classList.add('open');
}

function renderTierMembers(){
  const tier=state.tiers.find(item=>item.id===editingTierId);if(!tier)return;
  const deployments=tier.deployment_ids.map(id=>state.deployments.find(item=>item.id===id)).filter(Boolean);
  $('#tier-members').innerHTML=deployments.map(deployment=>{const status=backendState(deployment,state.providers.find(item=>item.id===deployment.provider_id),state.runtime.deployments[deployment.id]);return `<form class="member-card" data-deployment="${esc(deployment.id)}"><div class="member-heading"><b>${esc(deployment.name)}</b><span>${statusMarkup(status[0],status[1])}${esc(deployment.id)} · v${deployment.version}</span></div><label>Provider<select name="provider_id">${providerOptions(deployment.provider_id)}</select></label><label>Deployment Name<input name="name" value="${esc(deployment.name)}" required></label><label>Backend Model ID<input name="backend_model" value="${esc(deployment.backend_model)}" required></label><label class="check"><input name="enabled" type="checkbox" ${deployment.enabled?'checked':''}> Available for routing</label><div class="member-actions"><button type="button" class="danger member-remove">${iconSvg('unlink')}<span>Remove</span></button><button class="primary">${iconSvg('save')}<span>Save</span></button></div></form>`}).join('')||'<div class="empty compact">This tier has no members.</div>';
  $$('#tier-members .member-card').forEach(form=>{form.onsubmit=saveMember;form.querySelector('.member-remove').onclick=()=>removeMember(form.dataset.deployment)});
  $('#member-provider').innerHTML=providerOptions();
  $('#member-capability').textContent=tier.id==='Embedding-v1'?'Embeddings':'Responses';
  const addButton=$('#add-member-form button');
  addButton.disabled=!state.providers.length;
  addButton.title=state.providers.length?'':'Add a provider before adding a tier member';
}

async function saveMember(event){
  event.preventDefault();
  const form=event.currentTarget,deployment=state.deployments.find(item=>item.id===form.dataset.deployment);
  try{
    await api(`/tier/admin/v1/deployments/${encodeURIComponent(deployment.id)}`,{method:'PATCH',headers:{'If-Match':etag(deployment)},body:{provider_id:form.elements.provider_id.value,name:form.elements.name.value,backend_model:form.elements.backend_model.value,enabled:form.elements.enabled.checked}});
    await loadRegistry();renderTree();renderTierMembers();
  }catch(error){$('#tier-form-error').textContent=error.message}
}

async function removeMember(deploymentId){
  const tier=state.tiers.find(item=>item.id===editingTierId);if(!tier)return;
  const deployment=state.deployments.find(item=>item.id===deploymentId);
  if(!window.confirm(`Remove “${deployment?.name||deploymentId}” from ${tier.id}? The deployment will not be deleted.`))return;
  try{
    await api(`/tier/admin/v1/service-levels/${encodeURIComponent(tier.id)}`,{method:'PATCH',headers:{'If-Match':etag(tier)},body:{deployment_ids:tier.deployment_ids.filter(id=>id!==deploymentId)}});
    await loadRegistry();renderTree();renderTierMembers();
  }catch(error){$('#tier-form-error').textContent=error.message}
}

async function addMember(event){
  event.preventDefault();
  const form=event.currentTarget,tier=state.tiers.find(item=>item.id===editingTierId);if(!tier)return;
  const kind=tier.id==='Embedding-v1'?'embeddings':'responses';
  try{
    const deployment=await api('/tier/admin/v1/deployments',{method:'POST',body:{name:form.elements.name.value,provider_id:form.elements.provider_id.value,backend_model:form.elements.backend_model.value,capabilities:caps(kind),enabled:true}});
    await api(`/tier/admin/v1/service-levels/${encodeURIComponent(tier.id)}`,{method:'PATCH',headers:{'If-Match':etag(tier)},body:{deployment_ids:[...tier.deployment_ids,deployment.id]}});
    form.reset();await loadRegistry();renderTree();renderTierMembers();
  }catch(error){$('#tier-form-error').textContent=error.message}
}

async function loadUsage(){const page=await api('/tier/admin/v1/usage?'+windowQuery());$('#usage-body').innerHTML=page.data.map(item=>`<tr><td>${esc(item.request_id)}</td><td>${esc(item.model)}</td><td>${esc(item.endpoint)}</td><td>${item.input_tokens??'Unknown'}</td><td>${item.output_tokens??'Unknown'}</td><td>${item.total_tokens??'Unknown'}</td><td>${statusMarkup(item.measurement_status,item.measurement_status==='measured'?'ok':'warn')}</td></tr>`).join('')||'<tr><td colspan="7">No records</td></tr>'}
async function loadAudit(){const page=await api('/tier/admin/v1/audit');$('#audit-body').innerHTML=page.data.map(item=>`<tr><td>${new Date(item.created_at).toLocaleString()}</td><td>${esc(item.actor)}</td><td>${esc(item.action)}</td><td>${esc(item.target)}</td><td>${esc(item.result)}</td></tr>`).join('')||'<tr><td colspan="5">No records</td></tr>'}
async function loadLogs(){const query=new URLSearchParams(windowQuery());if($('#log-level').value)query.set('level',$('#log-level').value);if($('#log-module').value)query.set('module',$('#log-module').value);const page=await api('/tier/admin/v1/logs?'+query);$('#log-body').innerHTML=page.data.map(item=>`<tr><td>${new Date(item.created_at).toLocaleString()}</td><td>${esc(item.level)}</td><td>${esc(item.module)}</td><td>${esc(item.event)}</td><td>${esc(item.message)}</td><td>${esc(item.request_id||'—')}</td></tr>`).join('')||'<tr><td colspan="6">No records</td></tr>'}

$$('nav button').forEach(button=>button.onclick=()=>{
  $$('nav button').forEach(item=>item.classList.remove('active'));button.classList.add('active');
  $$('.page').forEach(item=>item.classList.remove('active'));$('#'+button.dataset.page).classList.add('active');
  const meta={home:['Home','View every model, tier, backend, and status on one page'],providers:['Providers','Manage cloud and local provider connections'],records:['Usage & Audit','Review token usage and administrative changes'],logs:['Logs','Review sanitized gateway runtime events']}[button.dataset.page];
  $('#title').textContent=meta[0];$('#subtitle').textContent=meta[1];
  if(button.dataset.page==='home')loadHome();if(button.dataset.page==='providers')loadProviders();if(button.dataset.page==='records')loadUsage();if(button.dataset.page==='logs')loadLogs();
});
$$('[data-tab]').forEach(button=>button.onclick=()=>{$$('[data-tab]').forEach(item=>item.classList.remove('active'));button.classList.add('active');$$('.sub').forEach(item=>item.classList.remove('active'));$('#'+button.dataset.tab).classList.add('active');button.dataset.tab==='audit'?loadAudit():loadUsage()});

$('#refresh-providers').onclick=loadProviders;$('#add-provider').onclick=()=>openProviderEditor();$('#provider-form').onsubmit=saveProvider;$('#close-provider').onclick=$('#cancel-provider').onclick=()=>$('#provider-mask').classList.remove('open');
$('#add-member-form').onsubmit=addMember;$('#close-tier').onclick=()=>$('#tier-mask').classList.remove('open');
$('#refresh-usage').onclick=loadUsage;$('#refresh-audit').onclick=loadAudit;$('#refresh-logs').onclick=loadLogs;

loadHome();
