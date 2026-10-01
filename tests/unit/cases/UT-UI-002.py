import unittest
from pathlib import Path


ROOT=Path(__file__).parents[3]/"src/web_ui"


class WebUIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.html=(ROOT/"index.html").read_text();cls.js=(ROOT/"app.js").read_text();cls.css=(ROOT/"styles.css").read_text();cls.icons=(ROOT/"icons.svg").read_text()
    def test_tier_member_editor_uses_existing_provider(self):
        self.assertIn('id="tier-mask"',self.html)
        self.assertIn('id="member-provider"',self.html)
        self.assertIn("'tier-edit'",self.js)
        self.assertIn("providerOptions()",self.js)
    def test_tier_parent_type_cell_is_empty(self):
        self.assertIn("</span><span>—</span><span></span><span>${iconButton('pencil'",self.js)
        self.assertNotIn("tier.capabilities.responses?'Responses':'Embeddings'",self.js)


