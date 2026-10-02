"""MT-UI-003 — `dispatchUiError` 五分支错误分派（M002 web-ui，层②，negative，P0）。

覆盖：`app.js` I9 错误分派的静态契约与语义——401 清会话跳登录且不回显
凭据；403 留在当前页、不猜存在性（固定文案，不回显服务端 message）；409
标记引用冲突并保留原 message；412 标记 staleEdit 并保留用户输入；429 读
`Retry-After` 头；503 标 stale；未列举状态交给 `reportLoadFailure`。外加
错误对象字段（`status`/`code`/`retry_after`）与 M001 `ApiError.envelope()`
的对应关系，以及 ENV-2 真实 loopback 上 401/403/503 的实际产出。

环境：**真实静态产物契约层 + ENV-2 loopback**（读 `src/web_ui/app.js` 文本，
与 `src/http_api/errors.py`、`src/http_api/auth.py`、`src/inference/routing.py`、
`src/inference/responses.py` 的 429 `Retry-After` 出口交叉断言；鉴权状态经
模块边界配置（进程环境变量）注入并在 127.0.0.1:0 上发真实请求，不经 LAN、
不触上游）。真实浏览器行为级归系统层 `ST-UI-*`。
"""
from __future__ import annotations

import os
import re
import unittest
from unittest.mock import patch

from http_api.errors import ApiError
from tests.module.cases.support import web_assets as assets
from tests.module.cases.support.http_env import PerTestLoopbackEnv

ENVELOPE_KEYS = {"message", "type", "code", "param", "retryable"}


class MTUI003DispatchUiError(assets.SourceContractMixin, unittest.TestCase):
    def setUp(self):
        self.js = assets.app_js()
        self.body = assets.function_body(self.js, "dispatchUiError")

    def _branch(self, status):
        """Return the source text of the `error.status===<status>` branch."""
        branches = re.split(r"(?=if\(error\.status===\d+\))", self.body)
        for branch in branches:
            if branch.startswith(f"if(error.status==={status})"):
                return branch.rstrip()
        raise AssertionError(f"no branch for status {status}")

    def test_dispatch_covers_exactly_the_designated_statuses(self):
        self.assertEqual([401, 403, 409, 412, 429, 503], assets.dispatch_ui_error_statuses())
        for status in (401, 403, 409, 412, 429, 503):
            self.assertIn(f"if(error.status==={status})", self.body)
        # 401/403/409/412/429 分支各自 return（先分流、再抛出给调用方）；503 是末分支
        for status in (401, 403, 409, 412, 429):
            self.assertIn("return", self._branch(status), status)
        self.assertTrue(self._branch(503).startswith("if(error.status===503)"))
        self.assertTrue(self.body.rstrip().endswith("}"))
        self.assertNotIn("else", self.body)
        # `api()` 统一走 dispatchUiError 后抛出
        api = assets.function_body(self.js, "api")
        self.has("dispatchUiError(error);throw error", api)
        self.has("error.status=response.status", api)
        self.has("error.code=payload.error?.code||null", api)
        self.has("error.retry_after=response.headers.get('Retry-After')", api)
        self.has("new Error(payload.error?.message||`${response.status} ${response.statusText}`)", api)

    def test_401_clears_the_session_and_redirects_without_echoing_credentials(self):
        branch = self._branch(401)
        self.assertEqual("if(error.status===401){document.body.classList.add('stale');"
                         "window.location.assign(LOGIN_URL);return}", branch)
        self.has("const LOGIN_URL='/login';", self.js)
        # 401 分支不回显任何凭据/错误正文
        self.lacks_all(("error.message", "Authorization", "Bearer", "token"), branch, "401")
        # M001 侧的 401 是 Bearer 缺失（M001 鉴权契约），UI 不回显
        self.has('raise ApiError(401, "authentication_required"', assets.auth_py())
        self.has('raise ApiError(403, "permission_denied"', assets.auth_py())

    def test_403_presents_a_fixed_banner_without_leaking_existence(self):
        branch = self._branch(403)
        self.assertEqual("if(error.status===403){showBanner('Permission denied — you do not have access "
                         "to perform this action.');return}", branch)
        # 固定文案：不插入 error.message（不猜资源是否存在）
        self.lacks("error.message", branch, "403")
        self.lacks("${", branch, "403")
        self.has('raise ApiError(403, "permission_denied"', assets.app_py())

    def test_409_flags_reference_conflict_and_keeps_the_server_message(self):
        branch = self._branch(409)
        self.has("error.referenceConflict=true;", branch)
        self.has("error.message=`Conflict — this reference is still in use. ${error.message||''}`.trim();", branch)
        self.has("showBanner(error.message);", branch)
        # 409 → 引用保留，不自动级联删除（设计 §7 P-UI-EDIT 步骤 5）
        self.has('raise ApiError(409, "resource_in_use"', assets.registry_py())
        self.has('raise ApiError(409, "resource_conflict"', assets.registry_py())

    def test_412_marks_a_stale_edit_and_keeps_the_draft(self):
        branch = self._branch(412)
        self.has("error.staleEdit=true;", branch)
        self.has("showBanner('Changed by others — reload and retry. Your input was kept.');", branch)
        # 保留草稿：412 分支不清表单、不重载、不覆盖输入
        self.lacks_all(("form.reset()", "loadRegistry", "loadHome", ".value=''", ".innerHTML="), branch, "412")
        self.has('raise ApiError(412, "version_conflict"', assets.registry_py())
        self.has('extra={"current_version": row["version"]}', assets.registry_py())

    def test_429_surfaces_retry_after_and_marks_the_view_stale(self):
        branch = self._branch(429)
        self.has("document.body.classList.add('stale');", branch)
        self.has("showBanner(`Too many requests — retry after "
                 "${error.retry_after?`${error.retry_after}s`:'a moment'}.`);", branch)
        # 503/429 不无限重试：分支里没有任何自动重排程
        self.lacks_all(("setTimeout", "setInterval", "while", "api("), branch, "429")
        # M001/M003 侧的 429 出口必须带 Retry-After
        self.has('429, "rate_limit_exceeded", "Service-level queue is full", retryable=True, '
                 'headers={"Retry-After": "30"}', assets.routing_py())
        self.has('headers={"Retry-After": "1"}', assets.routing_py())
        self.has('headers={"Retry-After": str(retry)}', assets.responses_py())

    def test_503_marks_stale_and_leaves_unlisted_statuses_to_report_load_failure(self):
        branch = self._branch(503)
        self.assertEqual("if(error.status===503){markStale('Service unavailable — showing the last known screen.')}",
                         branch.rstrip())
        mark = assets.function_body(self.js, "markStale")
        self.assertEqual("document.body.classList.add('stale');showBanner(message)", mark)
        self.has("function showBanner(message){const banner=$('#ui-banner');"
                 "if(banner){banner.textContent=message;banner.hidden=false}}", self.js)
        self.assertIn("ui-banner", assets.dom_ids())
        # 503/429 只标 stale，不清空任何业务容器
        for status in (429, 503):
            self.lacks_all((".innerHTML=", ".textContent="), self._branch(status), str(status))
        # 未列举状态（500/网络）不在 dispatchUiError 内处理 → 由 reportLoadFailure 承担
        self.assertNotIn("500", self.body)
        self.assertEqual([401, 403, 409, 412, 429, 503], assets.report_load_failure_suppressed())

    def test_error_object_fields_match_the_m001_error_envelope(self):
        self.assertEqual(ENVELOPE_KEYS, set(ApiError(500, "internal_error", "x").envelope()["error"]))
        api = assets.function_body(self.js, "api")
        # message / code 来自信封；retry_after 来自响应头（信封里没有该字段）
        self.has("payload.error?.message", api)
        self.has("payload.error?.code", api)
        self.has("response.headers.get('Retry-After')", api)
        self.lacks("error.param", api)
        self.lacks("error.retryable", api)
        self.lacks("payload.error?.retryable", api)
        # 服务端 5xx 归 server_error，4xx 归 request_error（UI 依 status 而非 type 分流）
        self.assertEqual("request_error", ApiError(404, "not_found", "x").envelope()["error"]["type"])
        self.assertEqual("server_error", ApiError(503, "usage_store_unavailable", "x").envelope()["error"]["type"])


class MTUI003RealAuthStatuses(assets.SourceContractMixin, PerTestLoopbackEnv):
    """401/403/503 由 M001 真实产出（ENV-2 loopback + 边界配置环境变量）。

    UI 的前两个分支按 status 呈现；这里验证这三个状态在组装后确实可达，
    且 401/403 的错误信封形状一致（不因资源是否存在而不同），以支撑 UI 侧
    固定文案的 403 横幅。
    """

    def test_real_401_and_403_share_the_same_envelope_shape(self):
        with patch.dict(os.environ, {"LLMTIER_ADMIN_TOKEN": "admin-secret", "LLMTIER_DEV_MODE": ""}, clear=False):
            missing, _, _ = self.request("GET", "/v1/providers", headers={"Authorization": "Basic abc"})
            wrong, payload, _ = self.request("GET", "/v1/providers", headers={"Authorization": "Bearer nope"})
        self.assertEqual(401, missing)
        self.assertEqual(403, wrong)
        self.assertEqual(ApiError(401, "authentication_required", "x").envelope()["error"].keys(),
                         payload["error"].keys())
        self.assertEqual("permission_denied", payload["error"]["code"])
        self.assertNotIn("retry_after", payload["error"])  # 429 才有，UI 从响应头读

    def test_unconfigured_auth_is_503_and_lands_in_the_same_503_branch(self):
        # 凭据未配置：清空两个 token 并关闭 dev 模式（dev 模式会自带凭据）
        with patch.dict(os.environ, {"LLMTIER_ADMIN_TOKEN": "", "LLMTIER_DATA_TOKEN": "",
                                     "LLMTIER_DEV_MODE": ""}, clear=False):
            status, payload, _ = self.request("GET", "/v1/providers", headers={"Authorization": "Bearer anything"})
        self.assertEqual(503, status)
        self.assertEqual("auth_not_configured", payload["error"]["code"])
        # 503（无论 store 还是 auth 面）都落 dispatchUiError 的同一分支
        self.assertIn("if(error.status===503){markStale('Service unavailable — showing the last known screen.')}",
                      assets.function_body(assets.app_js(), "dispatchUiError"))

    def test_retry_after_comes_from_the_header_not_the_envelope(self):
        # 429 出口在 M003 推理面（UI 不调用），故此处只断言信封不含该字段：
        # UI 必须从响应头读取，两个来源不混淆
        self.assertNotIn("retry_after", ApiError(429, "rate_limit_exceeded", "x").envelope()["error"])
        self.has("error.retry_after=response.headers.get('Retry-After')",
                 assets.function_body(assets.app_js(), "api"))


if __name__ == "__main__":
    unittest.main()
