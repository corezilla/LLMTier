import unittest
from pathlib import Path


ROOT=Path(__file__).parents[3]/"src/web_ui"


class WebUIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.html=(ROOT/"index.html").read_text();cls.js=(ROOT/"app.js").read_text();cls.css=(ROOT/"styles.css").read_text();cls.icons=(ROOT/"icons.svg").read_text()
    def test_home_shows_authoritative_backend_status(self):
        for value in ('Idle','Running','Paused','Probing','Exhausted','Unreachable','Disabled','Unknown'):
            self.assertIn(value,self.js)
        self.assertIn("(runtime.running||0)>0?'Running':'Idle'",self.js)
        self.assertIn("'backend-probe'",self.js)
        self.assertIn("'/v1/probes'",self.js)
        self.assertIn("if(!deployment.enabled)return ['Paused','muted']",self.js)
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
    def test_compact_icon_actions(self):
        self.assertIn('class="icon-button"',self.html)
        self.assertIn('iconButton(',self.js)
        self.assertIn('aria-label=',self.js)
        self.assertIn('class="ui-icon"',self.html)
        self.assertIn('class="status-icon',self.js)
        self.assertIn('title="${esc(label)}"',self.js)
        self.assertNotIn('&nbsp;${esc(label)}',self.js)


