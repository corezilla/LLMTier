"""Static-asset contract helpers for MT-UI-* module cases (M002).

M002 的**行为级**（真实 JS 执行）归系统层 `ST-UI-*`；模块层只做**真实产物
静态契约**断言：读 `src/web_ui/` 下真实的 `index.html` / `app.js` /
`icons.svg` 文本（与 M001 `_static` 交付的同一目录），抽出映射函数、判定
分支与 API 路径字面量，再与 M001 `app.py`、M004 `account_usage.py`、
M004 `registry.py` 的服务端契约交叉比对。

本模块只提供**提取**能力（正则 + 花括号配平），不含任何判定；判定与期望
值留在各 Case 文件内（§1.6「不耦合实现细节」之外的契约层断言）。
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import http_api.app
from http_api import auth, health
from inference import usage
from management import account_usage, admin, registry

SRC_ROOT = Path(http_api.app.__file__).resolve().parent.parent
WEB_UI = SRC_ROOT / "web_ui"


# ---------------------------------------------------------------- 真实产物
@lru_cache(maxsize=None)
def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def app_js() -> str:
    return _text(WEB_UI / "app.js")


def index_html() -> str:
    return _text(WEB_UI / "index.html")


def icons_svg() -> str:
    return _text(WEB_UI / "icons.svg")


# ---------------------------------------------------------------- 服务端源码
def app_py() -> str:
    return Path(http_api.app.__file__).read_text(encoding="utf-8")


def account_usage_py() -> str:
    return Path(account_usage.__file__).read_text(encoding="utf-8")


def registry_py() -> str:
    return Path(registry.__file__).read_text(encoding="utf-8")


def auth_py() -> str:
    return Path(auth.__file__).read_text(encoding="utf-8")


def health_py() -> str:
    return Path(health.__file__).read_text(encoding="utf-8")


def admin_py() -> str:
    return Path(admin.__file__).read_text(encoding="utf-8")


def usage_py() -> str:
    return Path(usage.__file__).read_text(encoding="utf-8")


def routing_py() -> str:
    return (SRC_ROOT / "inference/routing.py").read_text(encoding="utf-8")


def responses_py() -> str:
    return (SRC_ROOT / "inference/responses.py").read_text(encoding="utf-8")


# ---------------------------------------------------------------- JS 提取
def function_body(source: str, name: str) -> str:
    """Brace-balanced body of `function name(...)` (also matches `async function`)."""
    match = re.search(rf"function\s+{re.escape(name)}\s*\(", source)
    if match is None:
        raise AssertionError(f"function {name}() not found in the UI source")
    # Skip the parameter list first: default values may contain braces
    # (`runtime={}`), so the first `{` is not necessarily the body.
    index, depth = match.end(), 1
    while depth:
        char = source[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        index += 1
    start = source.index("{", index)
    depth = 0
    for index in range(start, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start + 1:index]
    raise AssertionError(f"unbalanced braces in function {name}()")


def status_icon_map() -> dict[str, str]:
    """`statusIconName` label -> icon name, from the real `app.js`."""
    source = app_js()
    match = re.search(r"const statusIconName=label=>\(\{(.*?)\}\[label\]\|\|'", source, re.S)
    if match is None:
        raise AssertionError("statusIconName map not found")
    return {key: icon for key, icon in re.findall(r"'?([A-Za-z ]+)'?:'([a-z0-9-]+)'", match.group(1))}


def status_icon_default() -> str:
    return re.search(r"const statusIconName=label=>\(\{.*?\}\[label\]\|\|'([a-z0-9-]+)'\);", app_js(), re.S).group(1)


def icon_symbols() -> set[str]:
    return set(re.findall(r'<symbol id="icon-([a-z0-9-]+)"', icons_svg()))


def api_paths() -> list[str]:
    """Every literal path handed to the `api()` fetch wrapper (template literals kept)."""
    return re.findall(r"api\((`[^`]*`|'[^']*')", app_js())


def dom_ids() -> set[str]:
    return set(re.findall(r'id="([^"]+)"', index_html()))


def dom_write_targets() -> set[str]:
    """Ids `app.js` assigns to (`innerHTML`/`textContent`/`className`/...)."""
    return set(re.findall(
        r"\$\('#([A-Za-z0-9_-]+)'\)\.(?:innerHTML|textContent|className|checked|disabled|value|hidden|title|setAttribute)",
        app_js()))


def dispatch_ui_error_statuses() -> list[int]:
    return [int(value) for value in re.findall(r"error\.status===(\d+)", function_body(app_js(), "dispatchUiError"))]


def report_load_failure_suppressed() -> list[int]:
    body = function_body(app_js(), "reportLoadFailure")
    return [int(value) for value in re.findall(r"(\d+)", re.search(r"\[([0-9,]+)\]", body).group(1))]


class SourceContractMixin:
    """Concise failure output for source-text contract assertions.

    `assertIn`/`assertNotIn` echo the whole haystack on failure, which for a
    ~15 KB `app.py` buries the actual mismatch; these report only the needle.
    """

    def has(self, needle: str, haystack: str, label: str = "") -> None:
        self.assertTrue(needle in haystack, f"{label or 'source'}: {needle!r} not found")

    def has_all(self, needles, haystack: str, label: str = "") -> None:
        for needle in needles:
            self.has(needle, haystack, label)

    def lacks(self, needle: str, haystack: str, label: str = "") -> None:
        self.assertFalse(needle in haystack, f"{label or 'source'}: {needle!r} unexpectedly found")

    def lacks_all(self, needles, haystack: str, label: str = "") -> None:
        for needle in needles:
            self.lacks(needle, haystack, label)
