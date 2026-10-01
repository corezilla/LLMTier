import unittest
from pathlib import Path


ROOT=Path(__file__).parents[3]/"src/web_ui"


class WebUIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.html=(ROOT/"index.html").read_text();cls.js=(ROOT/"app.js").read_text();cls.css=(ROOT/"styles.css").read_text();cls.icons=(ROOT/"icons.svg").read_text()
    def test_diagnostics_page(self):
        for token in ('data-page="diagnostics"','data-dtab="snapshots"','data-dtab="dstats"','data-dtab="traces"','data-dtab="inj"','id="snapshots-body"','id="dstats-body"','id="traces-body"','id="diag-toggle-snapshots"','id="diag-toggle-stats"'):
            self.assertIn(token,self.html)
        for token in ('/v1/diagnostics/snapshots','/v1/diagnostics/stats','/v1/diagnostics/traces','/v1/trace/','/v1/deployments/','loadSnapshots','loadDiagStats','loadTraces','loadInjections'):
            self.assertIn(token,self.js)
    def test_stats_page_present(self):self.assertIn('data-page="stats"',self.html);self.assertIn('id="stats-thead"',self.html);self.assertIn('id="stats-body"',self.html);self.assertIn('/v1/stats',self.js)


