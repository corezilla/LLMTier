import json
import tempfile
import unittest
from pathlib import Path

from llmtier_v03 import __version__
from llmtier_v03.app import Application, handler_factory


class StartupTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def settings(self,value=None):
        p=self.root/"settings.json";p.write_text(json.dumps(value or {"providers":[],"deployments":[],"service_levels":[]}));return str(p)
    def test_version(self):self.assertEqual(__version__,"0.3.0-dev")
    def test_valid_bootstrap(self):
        app=Application(str(self.root/"a.db"),self.settings());self.assertIsNone(app.bootstrap_error);app.store.close()
    def test_missing_settings_not_ready(self):
        app=Application(str(self.root/"b.db"),None);self.assertIsNotNone(app.bootstrap_error);app.store.close()
    def test_invalid_settings_not_ready(self):
        app=Application(str(self.root/"c.db"),self.settings({"bad":[]}));self.assertIsNotNone(app.bootstrap_error);app.store.close()
    def test_failed_bootstrap_has_no_provider(self):
        app=Application(str(self.root/"d.db"),self.settings({"bad":[]}));self.assertEqual(app.store.one("SELECT count(*) FROM providers")[0],0);app.store.close()
    def test_restart_ignores_missing_settings(self):
        db=str(self.root/"e.db");app=Application(db,self.settings());app.store.close();again=Application(db,str(self.root/"missing"));self.assertIsNone(again.bootstrap_error);again.store.close()
    def test_handler_factory(self):
        app=Application(str(self.root/"f.db"),self.settings());self.assertTrue(issubclass(handler_factory(app),__import__('http.server').server.BaseHTTPRequestHandler));app.store.close()
