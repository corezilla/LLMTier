"""MT-UI-006 — `reportLoadFailure` 抑制/未知分支（M002 web-ui，层②，negative，P1）。

覆盖装载失败兜底的两个分支：已列举状态（401/403/409/412/429/503）直接
`return`（这些已由 `dispatchUiError` 呈现，不重复提示、不重复标 stale）；其余
失败（网络中断/500/400/404 等）经 `markStale` 标 stale 并保留上一屏（只加
body 标记 + 横幅，不清空任何业务容器、不写空态）；无 status 的错误（fetch
直接 reject）同样不被抑制；成功重装经 `clearStale` 清标记。

环境：**真实静态产物契约层 + ENV-2 loopback**（读 `src/web_ui/app.js` /
`index.html` 文本；并用 `PerTestLoopbackEnv` 在 127.0.0.1:0 上观测 M001 真实
产出的状态码落进哪个分支；无 JS 执行、不经 LAN、不触上游）。真实浏览器
行为级归系统层 `ST-UI-*`。
"""
from __future__ import annotations

import re
import unittest

from tests.module.cases.support import web_assets as assets
from tests.module.cases.support.http_env import PerTestLoopbackEnv

SUPPRESSED = [401, 403, 409, 412, 429, 503]
# 保留「上一屏」的装载器：失败必须走 reportLoadFailure，成功必须清 stale
STALE_LOADERS = ("loadHome", "loadUsage", "loadAudit", "loadLogs")


class MTUI006ReportLoadFailure(assets.SourceContractMixin, unittest.TestCase):
    def setUp(self):
        self.js = assets.app_js()
        self.body = assets.function_body(self.js, "reportLoadFailure")

    def test_suppressed_set_is_exactly_the_set_dispatch_ui_error_already_presented(self):
        self.assertEqual(SUPPRESSED, assets.report_load_failure_suppressed())
        self.assertEqual(assets.dispatch_ui_error_statuses(), assets.report_load_failure_suppressed())
        # 分工：dispatchUiError 先分流并呈现，reportLoadFailure 只兜底其余状态
        api = assets.function_body(self.js, "api")
        self.has("dispatchUiError(error);throw error", api)
        # 抑制判定是函数第一条语句：任何 DOM 写入都在它之后
        first = self.body.strip().splitlines()[0].strip()
        self.assertEqual("if(error&&[401,403,409,412,429,503].includes(error.status))return;", first)

    def test_listed_statuses_return_without_touching_the_view(self):
        lines = [line.strip() for line in self.body.strip().splitlines()]
        self.assertEqual(2, len(lines), lines)
        self.assertEqual("if(error&&[401,403,409,412,429,503].includes(error.status))return;", lines[0])
        # 抑制分支只有 return：不重复横幅、不重复加 stale、不清空任何东西
        self.lacks_all(("markStale", "showBanner", "classList", "innerHTML", "textContent"), lines[0], "suppressed")

    def test_unlisted_failure_marks_stale_and_keeps_the_last_screen(self):
        self.assertEqual("markStale('Refresh failed — showing the last known data.');",
                         self.body.strip().splitlines()[-1].strip())
        mark = assets.function_body(self.js, "markStale")
        self.assertEqual("document.body.classList.add('stale');showBanner(message)", mark)
        banner = assets.function_body(self.js, "showBanner")
        # 只写全局横幅一个节点：业务容器一概不动 → 上一屏数据与表格全部保留
        self.has("const banner=$('#ui-banner');", banner)
        self.lacks_all(("#tree", "#usage-body", "#audit-body", "#log-body", "innerHTML"), self.body, "markStale path")
        self.assertIn("ui-banner", assets.dom_ids())
        # stale 是 body 级 class，样式与清除都由它承担
        self.has("document.body.classList.add('stale');", self.js)

    def test_failure_without_a_status_is_not_suppressed(self):
        # `error&&` 前缀：无 status（fetch 直接 reject 的网络错误）或 null 一律不抑制
        self.assertTrue(self.body.strip().startswith("if(error&&["))
        api = assets.function_body(self.js, "api")
        # `error.status` 只在 HTTP 非 2xx 分支赋值 → reject 出去的错误没有 status
        self.assertEqual(1, len(re.findall(r"error\.status=(?!=)", self.js)))
        self.assertIn("error.status=response.status", api)
        self.assertIn("if(!response.ok)", api)
        # 成功重装清标记（Stale → Loading → normal）
        clear = assets.function_body(self.js, "clearStale")
        self.assertIn("document.body.classList.remove('stale');", clear)
        self.assertIn("banner.hidden=true", clear)

    def test_last_screen_loaders_route_failures_here_and_clear_stale_on_success(self):
        for name in STALE_LOADERS:
            body = assets.function_body(self.js, name)
            self.assertIn("}catch(error){reportLoadFailure(error)}", body, name)
            self.has("clearStale()", body, name)
            catch = body[body.rindex("catch("):]
            # 失败分支不重写业务容器 → 上一屏保留（不显示空表、不覆盖为空洞）
            self.lacks_all((".innerHTML", ".textContent", "form.reset()", "location"), catch, name)

    def test_the_banner_never_shows_server_text_for_a_stale_refresh(self):
        # 兜底文案是固定串：不回显服务端 message（可能含资源名/路径）
        self.has("markStale('Refresh failed — showing the last known data.');", self.body)
        self.lacks_all(("error.message", "${"), self.body, "reportLoadFailure")


class MTUI006RealStatusRouting(assets.SourceContractMixin, PerTestLoopbackEnv):
    """M001 真实产出的状态码落进正确的兜底分支（ENV-2 loopback）。"""

    def test_real_400_and_404_are_outside_the_suppressed_set(self):
        # 400：缺时间窗（后端前置校验）
        status, payload, _ = self.request("GET", "/v1/logs")
        self.assertEqual(400, status)
        self.assertEqual("invalid_request", payload["error"]["code"])
        # 404：路由未命中
        status, payload, _ = self.request("GET", "/v1/no-such-endpoint")
        self.assertEqual(404, status)
        self.assertEqual("not_found", payload["error"]["code"])
        for observed in (400, 404):
            self.assertNotIn(observed, SUPPRESSED)
        # 两者都未列举 → 走 markStale 保留上一屏，而不是被静默吞掉
        self.assertIn("if(error.status===503){markStale(", assets.function_body(assets.app_js(), "dispatchUiError"))
        self.assertNotIn("400", assets.function_body(assets.app_js(), "dispatchUiError"))
        self.assertNotIn("404", assets.function_body(assets.app_js(), "dispatchUiError"))

    def test_real_409_and_412_are_inside_the_suppressed_set(self):
        provider = self.request("GET", "/v1/providers")[1]["data"][0]
        conflict, conflict_body, _ = self.request("DELETE", f"/v1/providers/{provider['id']}",
                                                 headers={"If-Match": f'"{provider["id"]}.v{provider["version"]}"'})
        stale, stale_body, _ = self.request("PATCH", f"/v1/providers/{provider['id']}", {"name": "x"},
                                            headers={"If-Match": '"stale.v999"'})
        self.assertEqual(409, conflict)
        self.assertEqual("resource_in_use", conflict_body["error"]["code"])
        self.assertEqual(412, stale)
        self.assertEqual("version_conflict", stale_body["error"]["code"])
        for observed in (conflict, stale):
            self.assertIn(observed, SUPPRESSED)
        # 由 dispatchUiError 独占呈现 → 报告只断言不重复提示
        dispatcher = assets.function_body(assets.app_js(), "dispatchUiError")
        self.assertIn("if(error.status===409)", dispatcher)
        self.assertIn("if(error.status===412)", dispatcher)

    def test_the_ui_page_load_calls_satisfy_the_window_precondition(self):
        # 三张带时间窗的表：后端缺 from/to 即 400，UI 每次都带上窗口
        for path in ("/v1/usage", "/v1/stats", "/v1/logs"):
            status, payload, _ = self.request("GET", path)
            self.assertEqual(400, status, path)
            self.assertEqual("from and to are required", payload["error"]["message"], path)
        js = assets.app_js()
        self.assertIn("const windowQuery=()=>{", js)
        self.assertIn("api('/v1/usage?'+windowQuery()", js)
        self.assertIn("new URLSearchParams(windowQuery())", js)
        self.assertIn("&group_by=${group}", assets.function_body(js, "loadStats"))
        # 诊断面用 since/until，M001 侧同样要求成对出现
        self.assertIn("?since=${encodeURIComponent(from)}&until=${encodeURIComponent(to)}", js)

    def test_real_500_and_503_exits_exist_in_m001(self):
        # 未列举分支的两个典型来源：未知异常 → 500 internal_error；存储不可读 → 503
        source = assets.app_py()
        self.has('self._json(500, ApiError(500, "internal_error", "Internal server error").envelope())', source)
        self.has('self._json(503, ApiError(503, "usage_store_unavailable", "Store is unavailable").envelope())', source)
        # 503 已被列举（dispatchUiError 标 stale）；500 未列举 → reportLoadFailure 标 stale
        self.assertIn(503, SUPPRESSED)
        self.assertNotIn(500, SUPPRESSED)


if __name__ == "__main__":
    unittest.main()
