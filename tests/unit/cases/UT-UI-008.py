import unittest
from pathlib import Path


ROOT=Path(__file__).parents[3]/"src/web_ui"




class WebUIBranchContractTests(unittest.TestCase):
    """M002 behavior branches (UT-UI-007/008/009/010) — STRING-CONTRACT ONLY.

    No JS execution host (node/jsdom) is available in this layer, so these
    assertions verify the source encodes the required branch/contract; they do
    NOT drive `app.js`. Behavior-level UI verification is the named gap G-UT-3
    (scheme §4). Treat every assertion here as a static contract check.
    """

    @classmethod
    def setUpClass(cls):
        cls.js = (ROOT / "app.js").read_text()

    @staticmethod
    def _function_body(source: str, name: str) -> str:
        start = source.index(f"function {name}(")
        # Find the parameter list's closing paren (default params may contain
        # braces, e.g. `runtime={}`), then the body's opening brace.
        paren = source.index("(", start)
        depth_p = 0
        for index in range(paren, len(source)):
            if source[index] == "(":
                depth_p += 1
            elif source[index] == ")":
                depth_p -= 1
                if depth_p == 0:
                    brace = source.index("{", index)
                    break
        depth = 0
        for index in range(brace, len(source)):
            if source[index] == "{":
                depth += 1
            elif source[index] == "}":
                depth -= 1
                if depth == 0:
                    return source[brace:index + 1]
        raise AssertionError(f"unterminated function {name}")


    def test_report_load_failure_keeps_last_screen(self):
        self.assertIn("function reportLoadFailure(error)", self.js)
        self.assertIn("[401,403,409,412,429,503].includes(error.status)", self.js)
        self.assertIn("markStale('Refresh failed — showing the last known data.')", self.js)





