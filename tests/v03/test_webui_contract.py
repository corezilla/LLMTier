import unittest
from pathlib import Path


ROOT=Path(__file__).parents[2]/"src/llmtier_v03/webui"


class WebUIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.html=(ROOT/"index.html").read_text();cls.js=(ROOT/"app.js").read_text();cls.css=(ROOT/"styles.css").read_text()
    def test_four_pages(self):self.assertEqual(self.html.count('class="page'),4)
    def test_home_is_default(self):self.assertIn('id="home" class="page active"',self.html)
    def test_fixed_tier_tree_target(self):self.assertIn('id="tree"',self.html)
    def test_provider_management_page(self):
        self.assertIn('data-page="providers"',self.html)
        self.assertIn('id="provider-form"',self.html)
        self.assertIn('id="add-provider"',self.html)
    def test_tier_member_editor_uses_existing_provider(self):
        self.assertIn('id="tier-mask"',self.html)
        self.assertIn('id="member-provider"',self.html)
        self.assertIn('class="tiny tier-edit"',self.js)
        self.assertIn("providerOptions()",self.js)
    def test_no_global_add_model(self):
        self.assertNotIn('Add Model',self.html)
        self.assertNotIn('id="model-form"',self.html)
    def test_usage_and_audit_tabs(self):self.assertIn('data-tab="usage"',self.html);self.assertIn('data-tab="audit"',self.html)
    def test_log_page(self):self.assertIn('id="log-body"',self.html)
    def test_no_bearer_storage(self):self.assertNotIn('localStorage',self.js);self.assertNotIn('Bearer ',self.js)
