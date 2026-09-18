import unittest
from pathlib import Path


ROOT=Path(__file__).parents[2]/"src/llmtier_v03/webui"


class WebUIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.html=(ROOT/"index.html").read_text();cls.js=(ROOT/"app.js").read_text();cls.css=(ROOT/"styles.css").read_text();cls.icons=(ROOT/"icons.svg").read_text()
    def test_four_pages(self):self.assertEqual(self.html.count('class="page'),4)
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
        self.assertIn("'/tier/admin/v1/probes'",self.js)
        self.assertIn("if(!deployment.enabled)return ['Paused','muted']",self.js)
    def test_model_pause_resume_uses_existing_deployment_patch(self):
        self.assertIn("'backend-toggle'",self.js)
        self.assertIn("body:{enabled:!deployment.enabled}",self.js)
        self.assertIn("'If-Match':etag(deployment)",self.js)
        self.assertIn("New requests will stop, but active requests will continue",self.js)
        self.assertIn("Available for routing",self.js)
    def test_header_shows_runtime_version_and_ui_update_time(self):
        self.assertIn('id="build-meta"',self.html)
        self.assertIn('id="tier-summary"',self.html)
        self.assertIn('id="model-summary"',self.html)
        self.assertIn('id="load-summary"',self.html)
        self.assertIn("api('/healthz')",self.js)
        self.assertIn("api('/tier/admin/v1/runtime')",self.js)
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
    def test_usage_and_audit_tabs(self):self.assertIn('data-tab="usage"',self.html);self.assertIn('data-tab="audit"',self.html)
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
        for value in ('Account Usage','Calls / Tokens','Running / Max'):
            self.assertIn(value,self.html)
        self.assertIn('max_concurrent',self.js)
        self.assertIn('Unknown',self.js)
    def test_no_bearer_storage(self):self.assertNotIn('localStorage',self.js);self.assertNotIn('Bearer ',self.js)
