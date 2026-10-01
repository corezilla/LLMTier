import unittest
from pathlib import Path


ROOT=Path(__file__).parents[3]/"src/web_ui"


class WebUIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.html=(ROOT/"index.html").read_text();cls.js=(ROOT/"app.js").read_text();cls.css=(ROOT/"styles.css").read_text();cls.icons=(ROOT/"icons.svg").read_text()
    def test_no_global_add_model(self):
        self.assertNotIn('Add Model',self.html)
        self.assertNotIn('id="model-form"',self.html)
    def test_usage_and_audit_tabs(self):self.assertIn('data-tab="usage"',self.html);self.assertIn('data-tab="audit"',self.html);self.assertIn('data-tab="events"',self.html)
    def test_log_page(self):self.assertIn('id="log-body"',self.html)
    def test_provider_and_tree_operational_fields(self):
        self.assertIn('id="provider-tree"',self.html)
        self.assertIn('class="tree"',self.html)
        self.assertIn('class="provider-row"',self.js)
        self.assertIn('class="backend"',self.js)
        self.assertIn('provider-usage-refresh',self.js)
        self.assertIn('provider-deployment-edit',self.js)
        self.assertIn('max_concurrent',self.js)
        self.assertIn('Unknown',self.js)


