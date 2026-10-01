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

    def test_dispatch_ui_error_branches(self):
        for token in ("error.status===401", "error.status===403", "error.status===409",
                      "error.status===412", "error.status===429", "error.status===503"):
            self.assertIn(token, self.js)
        self.assertIn("window.location.assign(LOGIN_URL)", self.js)
        self.assertIn("error.staleEdit=true", self.js)
        self.assertIn("error.retry_after", self.js)


    def test_backend_state_precedence(self):
        body = self._function_body(self.js, "backendState")
        disabled = body.index("if(!provider?.enabled)return ['Disabled','muted']")
        paused = body.index("if(!deployment.enabled)return ['Paused','muted']")
        # Precedence is ORDER, not mere presence: provider-disabled must be
        # checked before deployment-disabled inside the function body.
        self.assertLess(disabled, paused)

    def test_tier_state_unknown_when_availability_absent(self):
        body = self._function_body(self.js, "tierState")
        # Ordering inside tierState: empty-tier guard before availability
        # lookup, and Unknown returned as the final fallback.
        empty = body.index("if(!tier.deployment_ids.length)return ['Empty','muted']")
        availability = body.index("const availability=state.tierAvailability[tier.id]")
        unknown = body.index("return ['Unknown','muted']")
        self.assertLess(empty, availability)
        self.assertLess(availability, unknown)



