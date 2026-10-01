import unittest
from pathlib import Path


ROOT=Path(__file__).parents[3]/"src/web_ui"


class WebUIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.html=(ROOT/"index.html").read_text();cls.js=(ROOT/"app.js").read_text();cls.css=(ROOT/"styles.css").read_text();cls.icons=(ROOT/"icons.svg").read_text()
    def test_model_pause_resume_uses_existing_deployment_patch(self):
        self.assertIn("'backend-toggle'",self.js)
        self.assertIn("body:{enabled:!deployment.enabled}",self.js)
        self.assertIn("'If-Match':etag(deployment)",self.js)
        self.assertIn("New requests will stop, but active requests will continue",self.js)
        self.assertIn("enabled:true",self.js)


