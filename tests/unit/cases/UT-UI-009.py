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





    def test_usage_summary_four_states(self):
        body = self._function_body(self.js, "usageSummary")
        # Each state must map to its own output token, and the branches must be
        # ordered: not_refreshed -> unlimited -> Unavailable (!=='ok') -> ok.
        not_refreshed = body.index("snapshot.status==='not_refreshed'")
        self.assertIn("'<span class=\"unknown\">Not refreshed</span>'", body)
        unlimited = body.index("snapshot.status==='unlimited'")
        self.assertIn("'<span class=\"metric\">Unlimited</span>'", body)
        unavailable = body.index("snapshot.status!=='ok'")
        self.assertIn(">Unavailable</span>", body)
        self.assertLess(not_refreshed, unlimited)
        self.assertLess(unlimited, unavailable)
        # Unknown != 0: the metric helper renders null as Unknown, not 0, and the
        # ok-branch uses it for a null percent.
        self.assertIn("const metric=value=>value==null?'<span class=\"unknown\">Unknown</span>'", self.js)
        self.assertIn("metric(snapshot.percent==null?null:`${snapshot.percent}%`)", body)


