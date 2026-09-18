import unittest
from pathlib import Path


ROOT=Path(__file__).parents[2]/"src/llmtier_v03/webui"


class WebUIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.html=(ROOT/"index.html").read_text();cls.js=(ROOT/"app.js").read_text();cls.css=(ROOT/"styles.css").read_text()
    def test_four_pages(self):self.assertEqual(self.html.count('class="page'),4)
    def test_home_is_default(self):self.assertIn('id="home" class="page active"',self.html)
    def test_fixed_tier_tree_target(self):self.assertIn('id="tree"',self.html)
    def test_home_shows_authoritative_backend_status(self):
        for value in ('Running','Probing','Exhausted','Unreachable','Disabled','Unknown'):
            self.assertIn(value,self.js)
        self.assertIn("'backend-probe'",self.js)
        self.assertIn("'/tier/admin/v1/probes'",self.js)
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
    def test_provider_management_page(self):
        self.assertIn('data-page="providers"',self.html)
        self.assertIn('id="provider-form"',self.html)
        self.assertIn('id="add-provider"',self.html)
        self.assertIn('API Key Reference',self.html)
    def test_tier_member_editor_uses_existing_provider(self):
        self.assertIn('id="tier-mask"',self.html)
        self.assertIn('id="member-provider"',self.html)
        self.assertIn("'tier-edit'",self.js)
        self.assertIn("providerOptions()",self.js)
    def test_no_global_add_model(self):
        self.assertNotIn('Add Model',self.html)
        self.assertNotIn('id="model-form"',self.html)
    def test_usage_and_audit_tabs(self):self.assertIn('data-tab="usage"',self.html);self.assertIn('data-tab="audit"',self.html)
    def test_log_page(self):self.assertIn('id="log-body"',self.html)
    def test_compact_icon_actions(self):
        self.assertIn('class="icon-button"',self.html)
        self.assertIn('iconButton(',self.js)
        self.assertIn('aria-label=',self.js)
    def test_provider_and_tree_operational_fields(self):
        for value in ('Concurrency','Account Usage','Calls / Tokens','Running / Max'):
            self.assertIn(value,self.html)
        self.assertIn('max_concurrent',self.js)
        self.assertIn('Unknown',self.js)
    def test_no_bearer_storage(self):self.assertNotIn('localStorage',self.js);self.assertNotIn('Bearer ',self.js)
