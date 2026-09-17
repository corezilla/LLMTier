import unittest
from pathlib import Path


ROOT=Path(__file__).parents[2]/"src/llmtier_v03/webui"


class WebUIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.html=(ROOT/"index.html").read_text();cls.js=(ROOT/"app.js").read_text();cls.css=(ROOT/"styles.css").read_text()
    def test_three_pages(self):self.assertEqual(self.html.count('class="page'),3)
    def test_home_is_default(self):self.assertIn('id="home" class="page active"',self.html)
    def test_fixed_tier_tree_target(self):self.assertIn('id="tree"',self.html)
    def test_model_drawer(self):self.assertIn('id="model-form"',self.html)
    def test_usage_and_audit_tabs(self):self.assertIn('data-tab="usage"',self.html);self.assertIn('data-tab="audit"',self.html)
    def test_log_page(self):self.assertIn('id="log-body"',self.html)
    def test_no_bearer_storage(self):self.assertNotIn('localStorage',self.js);self.assertNotIn('Bearer ',self.js)
