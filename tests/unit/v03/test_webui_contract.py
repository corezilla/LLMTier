import unittest
from pathlib import Path


ROOT=Path(__file__).parents[3]/"src/web_ui"


class WebUIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.html=(ROOT/"index.html").read_text();cls.js=(ROOT/"app.js").read_text();cls.css=(ROOT/"styles.css").read_text();cls.icons=(ROOT/"icons.svg").read_text()
    def test_five_pages(self):self.assertEqual(self.html.count('class="page'),5)
    def test_diagnostics_page(self):
        for token in ('data-page="diagnostics"','data-dtab="snapshots"','data-dtab="dstats"','data-dtab="traces"','data-dtab="inj"','id="snapshots-body"','id="dstats-body"','id="traces-body"','id="diag-toggle-snapshots"','id="diag-toggle-stats"'):
            self.assertIn(token,self.html)
        for token in ('/v1/diagnostics/snapshots','/v1/diagnostics/stats','/v1/diagnostics/traces','/v1/trace/','/v1/deployments/','loadSnapshots','loadDiagStats','loadTraces','loadInjections'):
            self.assertIn(token,self.js)
    def test_stats_page_present(self):self.assertIn('data-page="stats"',self.html);self.assertIn('id="stats-thead"',self.html);self.assertIn('id="stats-body"',self.html);self.assertIn('/v1/stats',self.js)
    def test_home_is_default(self):self.assertIn('id="home" class="page active"',self.html)
    def test_fixed_tier_tree_target(self):self.assertIn('id="tree"',self.html)
    def test_tree_has_no_column_title_row(self):
        self.assertNotIn('class="tree-head"',self.html)
        self.assertNotIn('Tier / Backend</span><span>Status',self.html)
        self.assertIn('class="tree-card"',self.html)
        self.assertIn('.tree-card{background:transparent;border:0',self.css)
        self.assertIn('details[open] summary{background:transparent}',self.css)
        self.assertIn('.backend:before',self.css)
        self.assertNotIn('background:#fcfdff;border-top',self.css)
    def test_home_shows_authoritative_backend_status(self):
        for value in ('Idle','Running','Paused','Probing','Exhausted','Unreachable','Disabled','Unknown'):
            self.assertIn(value,self.js)
        self.assertIn("(runtime.running||0)>0?'Running':'Idle'",self.js)
        self.assertIn("'backend-probe'",self.js)
        self.assertIn("'/v1/probes'",self.js)
        self.assertIn("if(!deployment.enabled)return ['Paused','muted']",self.js)
    def test_model_pause_resume_uses_existing_deployment_patch(self):
        self.assertIn("'backend-toggle'",self.js)
        self.assertIn("body:{enabled:!deployment.enabled}",self.js)
        self.assertIn("'If-Match':etag(deployment)",self.js)
        self.assertIn("New requests will stop, but active requests will continue",self.js)
        self.assertIn("enabled:true",self.js)
    def test_header_shows_runtime_version_and_ui_update_time(self):
        self.assertIn('id="build-meta"',self.html)
        self.assertIn('id="tier-summary"',self.html)
        self.assertIn('id="model-summary"',self.html)
        self.assertIn('id="load-summary"',self.html)
        self.assertIn("api('/healthz')",self.js)
        self.assertIn("api('/v1/runtime')",self.js)
        self.assertIn("item.availability==='available'",self.js)
        self.assertIn('document.lastModified',self.js)
    def test_root_route_assets_remain_same_origin(self):
        self.assertIn('href="/ui/styles.css"',self.html)
        self.assertIn('src="/ui/app.js"',self.html)
        self.assertIn('/ui/icons.svg#icon-',self.html)
    def test_provider_management_page(self):
        self.assertIn('data-page="providers"',self.html)
        self.assertIn('id="provider-form"',self.html)
        self.assertIn('id="add-provider"',self.html)
        self.assertIn('API Key Reference',self.html)
        self.assertIn('Usage Source',self.html)
        self.assertIn('Max Concurrent Requests',self.html)
        self.assertIn('MiniMax uses its API key; no console cookie is required.',self.html)
        self.assertIn("'provider-usage-refresh'",self.js)
        self.assertIn('/usage`,{method:\'POST\'',self.js)
    def test_tier_member_editor_uses_existing_provider(self):
        self.assertIn('id="tier-mask"',self.html)
        self.assertIn('id="member-provider"',self.html)
        self.assertIn("'tier-edit'",self.js)
        self.assertIn("providerOptions()",self.js)
    def test_tier_parent_type_cell_is_empty(self):
        self.assertIn("</span><span>—</span><span></span><span>${iconButton('pencil'",self.js)
        self.assertNotIn("tier.capabilities.responses?'Responses':'Embeddings'",self.js)
    def test_tier_and_member_status_sources_are_independent(self):
        self.assertIn('state.tierAvailability=Object.fromEntries',self.js)
        self.assertIn("if(availability==='available')return ['Ready','ok']",self.js)
        self.assertIn('const overall=tierState(tier);',self.js)
        self.assertNotIn('tierState(tier,deployments)',self.js)
    def test_no_global_add_model(self):
        self.assertNotIn('Add Model',self.html)
        self.assertNotIn('id="model-form"',self.html)
    def test_usage_and_audit_tabs(self):self.assertIn('data-tab="usage"',self.html);self.assertIn('data-tab="audit"',self.html);self.assertIn('data-tab="events"',self.html)
    def test_log_page(self):self.assertIn('id="log-body"',self.html)
    def test_compact_icon_actions(self):
        self.assertIn('class="icon-button"',self.html)
        self.assertIn('iconButton(',self.js)
        self.assertIn('aria-label=',self.js)
        self.assertIn('class="ui-icon"',self.html)
        self.assertIn('class="status-icon',self.js)
        self.assertIn('title="${esc(label)}"',self.js)
        self.assertNotIn('&nbsp;${esc(label)}',self.js)
    def test_approved_icon_sprite_is_complete(self):
        for name in ('house','server','chart-no-axes-combined','logs','circle-check','circle-dot','activity','circle-pause','scan-search','gauge','triangle-alert','cloud-off','circle-off','circle-help','package-open','refresh-cw','plus','pencil','save','pause','play','trash-2','unlink','x'):
            self.assertIn(f'id="icon-{name}"',self.icons)
        self.assertIn("Idle:'circle-dot'",self.js)
        self.assertIn("Paused:'circle-pause'",self.js)
        self.assertIn("Running:'activity'",self.js)
    def test_provider_and_tree_operational_fields(self):
        self.assertIn('id="provider-tree"',self.html)
        self.assertIn('class="tree"',self.html)
        self.assertIn('class="provider-row"',self.js)
        self.assertIn('class="backend"',self.js)
        self.assertIn('provider-usage-refresh',self.js)
        self.assertIn('provider-deployment-edit',self.js)
        self.assertIn('max_concurrent',self.js)
        self.assertIn('Unknown',self.js)
    def test_no_bearer_storage(self):self.assertNotIn('localStorage',self.js);self.assertNotIn('Bearer ',self.js)


class WebUIBranchContractTests(unittest.TestCase):
    """M002 behavior branches (UT-UI-007/008/009/010) — STRING-CONTRACT ONLY.

    No JS execution host (node/jsdom) is available in this layer, so these
    assertions verify the source encodes the required branch/contract; they do
    NOT drive `app.js`. Behavior-level UI verification is the named gap G-UT-3
    (scheme §4). Treat every assertion here as a static contract check.
    """

    @classmethod
    def setUpClass(cls):
        cls.js = (ROOT / "app.js").read_text()

    def test_dispatch_ui_error_branches(self):
        for token in ("error.status===401", "error.status===403", "error.status===409",
                      "error.status===412", "error.status===429", "error.status===503"):
            self.assertIn(token, self.js)
        self.assertIn("window.location.assign(LOGIN_URL)", self.js)
        self.assertIn("error.staleEdit=true", self.js)
        self.assertIn("error.retry_after", self.js)

    def test_report_load_failure_keeps_last_screen(self):
        self.assertIn("function reportLoadFailure(error)", self.js)
        self.assertIn("[401,403,409,412,429,503].includes(error.status)", self.js)
        self.assertIn("markStale('Refresh failed — showing the last known data.')", self.js)

    def test_backend_state_precedence(self):
        self.assertIn("if(!provider?.enabled)return ['Disabled','muted']", self.js)
        self.assertIn("if(!deployment.enabled)return ['Paused','muted']", self.js)

    def test_tier_state_unknown_when_availability_absent(self):
        self.assertIn("const availability=state.tierAvailability[tier.id]", self.js)
        self.assertIn("if(!tier.deployment_ids.length)return ['Empty','muted']", self.js)
        self.assertIn("return ['Unknown','muted']", self.js)

    def test_usage_summary_four_states(self):
        self.assertIn("snapshot.status==='not_refreshed'", self.js)
        self.assertIn("snapshot.status==='unlimited'", self.js)
        self.assertIn("snapshot.status!=='ok'", self.js)
        self.assertIn("const metric=value=>", self.js)

    def test_stats_range_and_etag_and_model_cache(self):
        self.assertIn("function statsRange()", self.js)
        self.assertIn("const etag=item=>`\"${item.id}.v${item.version}\"`", self.js)
        self.assertIn("if(state.modelCache[providerId]) return state.modelCache[providerId]", self.js)
        self.assertIn("catch{return []}", self.js)

    def test_field_value_missing_returns_empty(self):
        self.assertIn("return element?element.value:''", self.js)
