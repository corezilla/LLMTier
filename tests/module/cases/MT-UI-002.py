"""MT-UI-002 — 组装后 UI API 契约（M002 web-ui，层①，normal，P0）。

覆盖：`app.js` 调用的每一条 `/v1/...` 路径都能在 M001 `app.py` 的路由里
找到；编辑流带 `If-Match` 且与 M004 `_etag` 格式一致；412/409 冲突时保留
用户输入不重载；Pause 确认边界、探测/用量刷新的付费确认；用量 Unknown
呈现；诊断 4 个 tab 与后端诊断端点一一对应；并用 ENV-2 真实 loopback
交叉验证 UI 依赖的状态码（412/409/400）确实由 M001+M004 产出。

环境：**真实静态产物契约层 + ENV-2 loopback**（读 `src/web_ui/app.js` /
`index.html` 文本，与 `src/http_api/app.py`、`src/management/registry.py`、
`admin.py`、`src/inference/usage.py` 交叉断言；`PerTestLoopbackEnv` 在
127.0.0.1:0 上发真实请求，不经 LAN、不触上游）。真实浏览器行为级归系统层
`ST-UI-*`。
"""
from __future__ import annotations

import re
import unittest

from tests.module.cases.support import web_assets as assets
from tests.module.cases.support.http_env import PerTestLoopbackEnv

# app.js 的 fetch 路径 → app.py 的路由判据（`<id>` 为路径参数占位；
# `/v1/<plural>/<id>` 三类资源由同一段 for 循环路由，故共用一条判据）
UI_PATH_CONTRACT = {
    "/v1/providers": ['path == "/v1/providers"'],
    "/v1/deployments": ['path == "/v1/deployments"'],
    "/v1/service-levels": ['path == "/v1/service-levels"'],
    "/v1/runtime": ['path == "/v1/runtime" and method == "GET"'],
    "/v1/usage": ['path == "/v1/usage"'],
    "/v1/probes": ['path == "/v1/probes" and method == "POST"'],
    "/v1/stats": ['re.fullmatch(r"/v1/stats", path)'],
    "/v1/audit": ['path == "/v1/audit" and method == "GET"'],
    "/v1/logs": ['path == "/v1/logs" and method == "GET"'],
    "/v1/diagnostics": ['path == "/v1/diagnostics" and method == "GET"',
                        'path == "/v1/diagnostics" and method == "PATCH"'],
    "/v1/diagnostics/snapshots": ['path == "/v1/diagnostics/snapshots" and method == "GET"'],
    "/v1/diagnostics/stats": ['path == "/v1/diagnostics/stats" and method == "GET"'],
    "/v1/diagnostics/traces": ['path == "/v1/diagnostics/traces" and method == "GET"'],
    "/v1/trace/<id>": ['re.fullmatch(r"/v1/trace/([^/]+)", path)'],
    "/v1/providers/<id>": ['fr"/v1/{plural}/([^/]+)"'],
    "/v1/deployments/<id>": ['fr"/v1/{plural}/([^/]+)"'],
    "/v1/service-levels/<id>": ['fr"/v1/{plural}/([^/]+)"'],
    "/v1/providers/<id>/usage": ['re.fullmatch(r"/v1/providers/([^/]+)/usage", path)'],
    "/v1/providers/<id>/models": ['re.fullmatch(r"/v1/providers/([^/]+)/models", path)'],
    "/v1/deployments/<id>/diagnostics": ['re.fullmatch(r"/v1/deployments/([^/]+)/diagnostics", path)'],
    "/healthz": ['path == "/healthz" and method == "GET"'],
    "/readyz": ['path == "/readyz" and method == "GET"'],
}
DIAG_TABS = {"snapshots": ("loadSnapshots", "/v1/diagnostics/snapshots", "snapshots-body"),
             "dstats": ("loadDiagStats", "/v1/diagnostics/stats", "dstats-body"),
             "traces": ("loadTraces", "/v1/diagnostics/traces", "traces-body"),
             "inj": ("loadInjections", "/diagnostics", "inj-body")}


class MTUI002ApiContract(assets.SourceContractMixin, unittest.TestCase):
    def setUp(self):
        self.js = assets.app_js()
        self.py = assets.app_py()

    def test_every_api_path_used_by_app_js_exists_in_the_m001_router(self):
        used = {path.strip("`'").split("?")[0] for path in assets.api_paths()}
        used |= {"/readyz"}  # loadHome 用 fetch() 直取 /readyz
        keys = {re.sub(r"\$\{[^}]*\}", "<id>", path) for path in used}
        # UI 未调用任何 M001 未暴露的端点
        self.assertEqual(set(), keys - set(UI_PATH_CONTRACT))
        for path in sorted(used):
            key = re.sub(r"\$\{[^}]*\}", "<id>", path)
            for route in UI_PATH_CONTRACT[key]:
                self.has(route, self.py, f"M001 route for {path}")
        # 21 条 fetch 路径 + /readyz 全部落在已登记契约里
        self.assertEqual(22, len(used))

    def test_etag_format_matches_the_registry_writer(self):
        # app.js：`"<id>.v<version>"`；M004 registry.py：`f'"{resource_id}.v{version}"'`
        self.has('const etag=item=>`"${item.id}.v${item.version}"`;', self.js, "app.js ETag")
        self.has("""return f'"{resource_id}.v{version}"'""", assets.registry_py(), "M004 ETag")
        self.has("headers:{'If-Match':etag(deployment)}", assets.function_body(self.js, "saveMember"))
        self.has("headers:{'If-Match':etag(tier)}", assets.function_body(self.js, "removeMember"))
        self.has("headers:{'If-Match':etag(provider)}", assets.function_body(self.js, "deleteProvider"))
        self.has("If-Match':`\"${id}.v${form.elements.provider_version.value}\"`",
                 assets.function_body(self.js, "saveProvider"))
        # M001 把 If-Match 原样透传给 M004 版本判定
        self.has('self.headers.get("If-Match")', self.py, "M001 If-Match passthrough")
        self.has('412, "version_conflict"', assets.registry_py(), "M004 412")

    def test_conflict_responses_keep_the_operator_input(self):
        js = self.js
        # 409/412 经 api() → dispatchUiError → 抛出；各 mutation 的 catch 只呈现错误、不重载
        for name, node in (("saveProvider", "#provider-form-error"), ("saveMember", "#tier-form-error"),
                           ("removeMember", "#tier-form-error"), ("addMember", "#tier-form-error"),
                           ("deleteProvider", "#provider-error")):
            body = assets.function_body(js, name)
            catch = body[body.rindex("catch("):]
            self.has(f"$('{node}').textContent=error.message", catch, name)
            self.lacks_all(("loadRegistry", "loadHome", "loadProviders", "renderTree", "form.reset"),
                            catch, f"{name} catch")
        # 412 分支声明 staleEdit，409 分支声明 referenceConflict（保留输入 / 禁强删）
        dispatcher = assets.function_body(js, "dispatchUiError")
        self.has("error.staleEdit=true;", dispatcher)
        self.has("error.referenceConflict=true;", dispatcher)
        self.has("Your input was kept.", dispatcher)
        # 409 只增补冲突前缀，服务端 message 原样保留
        self.has("error.message=`Conflict — this reference is still in use. ${error.message||''}`.trim();", dispatcher)

    def test_pause_requires_confirmation_only_when_requests_are_running(self):
        toggle = assets.function_body(self.js, "toggleDeployment")
        self.has("if(deployment.enabled&&(runtime.running||0)>0&&!window.confirm("
                 "'Pause this model? New requests will stop, but active requests will continue.'))return;", toggle)
        self.has("body:{enabled:!deployment.enabled}", toggle)  # Resume 仅翻转路由资格
        self.has("const toggleName=deployment.enabled?'pause':'play',"
                 "toggleLabel=deployment.enabled?'Pause model':'Resume model';",
                 assets.function_body(self.js, "renderTree"))
        # 确认前不发任何写请求
        self.assertLess(toggle.index("window.confirm"), toggle.index("api("))
        # Probe 按钮在 Disabled/Paused 状态下禁用（无确认机会）
        self.has("status[0]==='Disabled'||status[0]==='Paused'?'disabled':''",
                 assets.function_body(self.js, "renderTree"))

    def test_probe_and_usage_refresh_require_explicit_confirmation(self):
        probe = assets.function_body(self.js, "probeDeployment")
        self.has("if(!window.confirm('Probe this backend now? This makes one provider request.'))return;", probe)
        self.has("api('/v1/probes',{method:'POST',body:{deployment_id:deploymentId,confirm_external_call:true}})",
                 probe)
        refresh = assets.function_body(self.js, "refreshProviderUsage")
        self.has("if(!window.confirm(", refresh)
        self.has("confirm_external_call:true", refresh)
        self.assertLess(refresh.index("window.confirm"), refresh.index("api("))
        # M001/M004 侧：缺确认即 400 confirmation_required
        self.has('path == "/v1/probes" and method == "POST"', self.py)
        self.has('require(body.get("confirm_external_call") is True and set(body) == {"deployment_id", '
                 '"confirm_external_call"}, 400, "confirmation_required"', assets.admin_py())
        self.has('if set(body) != {"confirm_external_call"}:', self.py)
        self.has('require(confirm_external_call is True, 400, "confirmation_required"', assets.account_usage_py())

    def test_usage_view_renders_unknown_instead_of_zero(self):
        # 度量助手：null → Unknown（class="unknown"），非 null → metric
        self.has("const metric=value=>value==null?'<span class=\"unknown\">Unknown</span>'"
                 ":`<span class=\"metric\">${esc(value)}</span>`;", self.js)
        usage_view = assets.function_body(self.js, "loadUsage")
        for field in ("input_tokens", "output_tokens", "total_tokens"):
            self.has("${item.%s??'Unknown'}" % field, usage_view, field)
        tree = assets.function_body(self.js, "renderTree")
        # 任一行未知 → 合计 Unknown（不补零）
        self.has("const tierTokens=usage.some(item=>item.total_tokens==null)?null:"
                 "usage.reduce((sum,item)=>sum+item.total_tokens,0);", tree)
        self.has("metric(usage.length?`${usage.length} calls · ${tierTokens??'Unknown'} tok`:'No calls')", tree)
        # 后端行不持久化因子模型用量 → 显式 `—` + 边界说明，不显示 0
        self.has('title="Usage is recorded by Tier; the selected backend is not persisted"', tree)
        self.has("metric(`${runtime.running??0} / ${runtime.max_concurrent??'?'}`)", tree)
        # 版本替换：Usage 页只读 /v1/usage，M003 只回 head 版本（同一 request_id 不累计）
        self.has("api('/v1/usage?'+windowQuery())", usage_view)
        self.has("JOIN usage_record_versions v ON v.principal_id=h.principal_id AND v.request_id=h.request_id "
                 "AND v.record_version=h.head_record_version", assets.usage_py())

    def test_diagnostics_tabs_are_wired_to_the_four_backend_faces(self):
        html = assets.index_html()
        self.assertEqual(set(DIAG_TABS), set(re.findall(r'data-dtab="([a-z]+)"', html)))
        self.assertEqual(set(DIAG_TABS), set(re.findall(r'<div id="([a-z]+)" class="dsub', html)))
        loader = assets.function_body(self.js, "loadDiagnostics")
        for tab, (function, route, node) in DIAG_TABS.items():
            self.has(f"if(tab==='{tab}')await {function}()", loader, tab)
            self.has(route, assets.function_body(self.js, function), tab)
            self.has(node, assets.function_body(self.js, function), tab)
        # 开关：两个 checkbox 一次性 PATCH 两个布尔量，与 M001 允许的字段集一致
        self.has("api('/v1/diagnostics',{method:'PATCH',"
                 "body:{snapshots_enabled:$('#diag-toggle-snapshots').checked,"
                 "stats_enabled:$('#diag-toggle-stats').checked}})",
                 assets.function_body(self.js, "saveDiagSwitches"))
        self.has('if not set(body) <= {"snapshots_enabled", "stats_enabled"}:', self.py)
        self.has("diagState.snapshotsEnabled=!!s.snapshots_enabled;diagState.statsEnabled=!!s.stats_enabled;",
                 assets.function_body(self.js, "loadDiagSwitches"))
        # 关闭态：显示 Disabled 行且**不**发查询请求
        for function, node in (("loadSnapshots", "Disabled — enable Snapshots to record"),
                               ("loadDiagStats", "Disabled — enable Stats to record")):
            body = assets.function_body(self.js, function)
            guard = body[:body.index("const {from,to}=diagWindow()")]
            self.has(node, guard, function)
            self.lacks("api(", guard, function)
        # trace 详情按行取单请求视图；注入面板按 deployment 取注入列表
        self.has("api(`/v1/trace/${encodeURIComponent(requestId)}`)", assets.function_body(self.js, "showTrace"))
        self.has("api(`/v1/deployments/${encodeURIComponent(did)}/diagnostics`)",
                 assets.function_body(self.js, "loadInjections"))
        # 诊断错误统一进 #diag-error（局部呈现，不清空整页）
        self.has("$('#diag-error').textContent=error.message;", assets.function_body(self.js, "loadDiagnostics"))


class MTUI002BackendStatusCrossCheck(PerTestLoopbackEnv):
    """UI 依赖的状态码/ETag 形态与 M001+M004 的真实响应一致（ENV-2 loopback）。

    静态断言只能证明 `app.js` 写了什么；这里用真实 loopback 请求证明 UI 的
    编辑/探测/用量契约在**组装后**确实成立：旧 ETag 真的得 412、被引用资源
    真的得 409、未确认的付费操作真的被拒。
    """

    def _provider(self):
        return self.request("GET", "/v1/providers")[1]["data"][0]

    def test_stale_if_match_really_yields_412_for_every_resource_the_ui_edits(self):
        provider = self._provider()
        deployment = self.request("GET", "/v1/deployments")[1]["data"][0]
        # app.js 的 etag(item) → `"<id>.v<version>"`；用同形态的过期版本号
        stale = {"If-Match": '"stale.v999"'}
        for path, body in ((f"/v1/providers/{provider['id']}", {"name": "renamed"}),
                           (f"/v1/deployments/{deployment['id']}", {"enabled": False}),
                           ("/v1/service-levels/Worker", {"deployment_ids": []})):
            status, payload, _ = self.request("PATCH", path, body, headers=stale)
            self.assertEqual(412, status, path)
            self.assertEqual("version_conflict", payload["error"]["code"], path)
            # 412 信封带当前版本：UI 的「reload and retry」提示据此可操作
            self.assertIn("current_version", payload["error"], path)
        # 资源未被改动（412 是无副作用拒绝）
        self.assertEqual(provider["version"], self._provider()["version"])
        self.assertTrue(self.request("GET", "/v1/deployments")[1]["data"][0]["enabled"])

    def test_deleting_a_referenced_provider_really_yields_409_resource_in_use(self):
        provider = self._provider()
        etag = f'"{provider["id"]}.v{provider["version"]}"'
        status, payload, _ = self.request("DELETE", f"/v1/providers/{provider['id']}", headers={"If-Match": etag})
        self.assertEqual(409, status)
        self.assertEqual("resource_in_use", payload["error"]["code"])
        # 引用保留：provider 仍在（UI 的 409 分支不级联删除）
        self.assertEqual([provider["id"]], [item["id"] for item in self.request("GET", "/v1/providers")[1]["data"]])

    def test_fixed_service_level_delete_really_yields_409_not_412(self):
        status, payload, _ = self.request("DELETE", "/v1/service-levels/Senior",
                                          headers={"If-Match": '"Senior.v1"'})
        self.assertEqual(409, status)
        self.assertEqual("fixed_service_level", payload["error"]["code"])

    def test_probe_and_usage_refresh_really_reject_unconfirmed_calls(self):
        provider = self._provider()
        deployment = self.request("GET", "/v1/deployments")[1]["data"][0]
        # 缺 confirm_external_call 的探测
        status, payload, _ = self.request("POST", "/v1/probes", {"deployment_id": deployment["id"]})
        self.assertEqual(400, status)
        self.assertEqual("confirmation_required", payload["error"]["code"])
        # 显式 false 的用量刷新：路由层先校验 body 形状，服务层再校验确认位
        status, payload, _ = self.request("POST", f"/v1/providers/{provider['id']}/usage",
                                          {"confirm_external_call": False})
        self.assertEqual(400, status)
        self.assertEqual("confirmation_required", payload["error"]["code"])
        # 多余字段同样被拒（app.js 只发 deployment_id + confirm_external_call）
        status, payload, _ = self.request("POST", "/v1/probes",
                                          {"deployment_id": deployment["id"], "confirm_external_call": True, "extra": 1})
        self.assertEqual(400, status)
        self.assertEqual("confirmation_required", payload["error"]["code"])

    def test_confirmed_probe_really_dispatch_and_report_cost_flag(self):
        deployment = self.request("GET", "/v1/deployments")[1]["data"][0]
        status, payload, _ = self.request("POST", "/v1/probes",
                                          {"deployment_id": deployment["id"], "confirm_external_call": True})
        self.assertEqual(200, status)
        # UI 的探测确认语义：服务端回报「可能已产生费用」标志
        self.assertIn("may_have_incurred_cost", payload)
        self.assertIn(payload["status"], ("healthy", "unhealthy"))
        # 探测结果落回 deployment.health（backendState 的输入）
        self.assertEqual(payload["status"], self.request("GET", "/v1/deployments")[1]["data"][0]["health"])


if __name__ == "__main__":
    unittest.main()

