"""Case ID: ST-SCAN-001

Endpoint: GET /healthz（活体响应头扫描）+ 静态 OpenAPI/manifest 扫描
Upstream Provider: 无
Model: 无
Auth: 无（/healthz 为 security:[] 公共端点）

TS-002 依赖：
  Endpoint: 临时 LLMTier 实例（llmtier_b_empty，空 settings），127.0.0.1:<临时端口>
  上游: 无（仅 /healthz）
  Auth: 无（裸客户端）

目标：absence/边界扫描——退役接口不得回潮。扫描机器契约与活体响应：
- OpenAPI `paths` 不含 forbidden 路径（`/call`、`/admin/v0/*`、`/legacy/`）
- 兼容清单 capability.path 不含 forbidden 路径
- 活体 /healthz 响应头不含 forbidden 头前缀（`X-Legacy-*`）与框架版本号
- 请求携带的敏感头不得被回显到响应头/响应体

设计验证项：无运行层 VRC（absence 静态契约承接，见方案 §4；对应
`CT-SCOPE-001`/`CT-BOUNDARY-001`）。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
OPENAPI = REPO / "interfaces" / "openapi" / "llmtier.openapi.json"
MANIFEST = REPO / "interfaces" / "compatibility" / "compatibility-manifest-v0.3.json"

FORBIDDEN_PATH_PATTERNS = [
    r"^/call$",
    r"^/call/",
    r"^/admin/v0/.*$",
    r"/legacy/",
    r"/admin/v0\.",
]
FORBIDDEN_HEADER_PREFIXES = ("X-Legacy-",)


def _openapi_paths(doc: dict) -> set[str]:
    paths: set[str] = set()
    for path, methods in doc.get("paths", {}).items():
        for method in methods:
            if method.lower() in {"get", "post", "put", "patch", "delete", "head", "options"}:
                paths.add(path)
    return paths


@pytest.mark.api_b
def test_scan_01_no_legacy_path_in_openapi():
    doc = json.loads(OPENAPI.read_text(encoding="utf-8"))
    offenders = [
        p for p in _openapi_paths(doc)
        if any(re.match(pat, p) for pat in FORBIDDEN_PATH_PATTERNS)
    ]
    assert offenders == [], f"legacy 路径泄漏进 OpenAPI: {offenders}"


@pytest.mark.api_b
def test_scan_02_no_legacy_path_in_manifest():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    text = MANIFEST.read_text(encoding="utf-8")
    assert '"/call"' not in text, "manifest 含 forbidden 字面 '\"/call\"'"
    assert '"/admin/v0' not in text, "manifest 含 forbidden 字面 '\"/admin/v0'"
    for cap in manifest.get("capabilities", []):
        path = cap.get("path", "")
        for pat in FORBIDDEN_PATH_PATTERNS:
            assert re.match(pat, path) is None, (
                f"manifest capability path {path!r} 命中 forbidden {pat!r}"
            )


@pytest.mark.api_b
def test_scan_03_healthz_no_legacy_header(llmtier_b_empty):
    resp = llmtier_b_empty.api_client().get("/healthz")
    assert resp.status_code == 200, f"/healthz 返回 {resp.status_code}: {resp.text}"
    for prefix in FORBIDDEN_HEADER_PREFIXES:
        bad = [k for k in resp.headers.keys() if k.lower().startswith(prefix.lower())]
        assert bad == [], f"/healthz 含 forbidden 响应头前缀 {prefix}: {bad}"
    server = resp.headers.get("Server", "")
    assert "0.3.0" not in server, f"Server 头暴露框架版本: {server!r}"


@pytest.mark.api_b
def test_scan_04_healthz_no_sensitive_header_echo(llmtier_b_empty):
    resp = llmtier_b_empty.api_client().get(
        "/healthz", headers={"X-Custom-Auth": "Bearer probe-secret"}
    )
    assert resp.status_code == 200, f"/healthz 返回 {resp.status_code}: {resp.text}"
    for key, value in resp.headers.items():
        assert "probe-secret" not in value, f"敏感值被回显到响应头 {key}"
    assert "probe-secret" not in resp.text, "敏感值被回显到响应体"
