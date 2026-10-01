import unittest
from pathlib import Path


ROOT=Path(__file__).parents[3]/"src/web_ui"


class WebUIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.html=(ROOT/"index.html").read_text();cls.js=(ROOT/"app.js").read_text();cls.css=(ROOT/"styles.css").read_text();cls.icons=(ROOT/"icons.svg").read_text()
    def test_five_pages(self):self.assertEqual(self.html.count('class="page'),5)
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
    def test_tier_and_member_status_sources_are_independent(self):
        self.assertIn('state.tierAvailability=Object.fromEntries',self.js)
        self.assertIn("if(availability==='available')return ['Ready','ok']",self.js)
        self.assertIn('const overall=tierState(tier);',self.js)
        self.assertNotIn('tierState(tier,deployments)',self.js)
    def test_approved_icon_sprite_is_complete(self):
        for name in ('house','server','chart-no-axes-combined','logs','circle-check','circle-dot','activity','circle-pause','scan-search','gauge','triangle-alert','cloud-off','circle-off','circle-help','package-open','refresh-cw','plus','pencil','save','pause','play','trash-2','unlink','x'):
            self.assertIn(f'id="icon-{name}"',self.icons)
        self.assertIn("Idle:'circle-dot'",self.js)
        self.assertIn("Paused:'circle-pause'",self.js)
        self.assertIn("Running:'activity'",self.js)
    def test_no_bearer_storage(self):self.assertNotIn('localStorage',self.js);self.assertNotIn('Bearer ',self.js)


