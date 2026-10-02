"""MT-UI-005 — `usageSummary` 四态（M002 web-ui，层②，boundary，P1）。

覆盖账号用量渲染的四个分支：快照缺失/`not_refreshed`→"Not refreshed"、
`unlimited`→"Unlimited"、非 `ok`（`unavailable`/`unsupported`/…）→
"Unavailable" 且带 `error` 提示（**不**显示空表）、`ok`→逐 window 渲染
`name` + `percent`；`percent` 为 null 显示 Unknown 而非 0%；M004 只回
head 版本（版本替换、不累计）；503 走 stale 分支，保留上一屏表格；并用
ENV-2 真实 loopback 验证后端真实产出的快照状态逐个落进不同渲染分支。

环境：**真实静态产物契约层 + ENV-2 loopback**（读 `src/web_ui/app.js` 文本，
与 `src/management/account_usage.py`（`_snapshot`/`_window` 状态与字段）、
`src/inference/usage.py` 交叉断言；并经公开入口 `PATCH /v1/providers/{id}` +
`GET|POST /v1/providers/{id}/usage` 在 127.0.0.1:0 上取真实快照；不经 LAN、
不触上游）。真实浏览器行为级归系统层 `ST-UI-*`。
"""
from __future__ import annotations

import re
import unittest

from tests.module.cases.support import web_assets as assets
from tests.module.cases.support.http_env import PerTestLoopbackEnv

WINDOW_FIELDS = {"name", "used", "quota", "remaining", "percent", "reset_at"}
STATUSES = ("not_refreshed", "unlimited", "unavailable", "ok")


class MTUI005UsageSummary(assets.SourceContractMixin, unittest.TestCase):
    def setUp(self):
        self.js = assets.app_js()
        self.body = assets.function_body(self.js, "usageSummary")
        self.service = assets.account_usage_py()

    def test_not_refreshed_is_the_first_branch_and_covers_a_missing_snapshot(self):
        self.has("if(!snapshot||snapshot.status==='not_refreshed')"
                 "return '<span class=\"unknown\">Not refreshed</span>';", self.body)
        # M004 侧：未刷新时 status=not_refreshed；凭据缺失的 provider 直接 unavailable
        self.has('return _snapshot(usage_provider, "store", "not_refreshed")', self.service)
        self.has('"not_refreshed"', self.service)
        # 呈现语义：Unknown 样式，不是 0，也不是空表
        self.has('<span class="unknown">Not refreshed</span>', self.body)
        self.lacks("0%", self.body)

    def test_unlimited_renders_a_metric_not_a_percentage(self):
        self.has("if(snapshot.status==='unlimited')return '<span class=\"metric\">Unlimited</span>';", self.body)
        # M004 侧：local provider 的用量配置是 unlimited
        self.has('elif usage_provider == "local": snapshot = _snapshot("local", "quota_config", "unlimited")', self.service)
        self.lacks("%", self.body.split("unlimited")[1].split("return")[0])

    def test_any_non_ok_status_becomes_unavailable_with_the_error_reason(self):
        self.has("if(snapshot.status!=='ok')return `<span class=\"unknown\" "
                 "title=\"${esc(snapshot.error||'Usage unavailable')}\">Unavailable</span>`;", self.body)
        self.has("snapshot.error", self.body)
        # 四态：显式两态 + ok + 兜底「非 ok 即 Unavailable」（对 M004 的全部状态与未知状态都成立）
        self.assertEqual({"not_refreshed", "unlimited"}, set(re.findall(r"status==='([a-z_]+)'", self.body)))
        self.has("snapshot.status!=='ok'", self.body)
        produced = {status for _, status in
                    re.findall(r'_snapshot\([^)]*?,\s*"([a-z_]+)"\s*,\s*"([a-z_]+)"', self.service)}
        self.assertEqual({"not_refreshed", "unavailable", "ok", "unlimited", "unsupported"}, produced)
        self.assertTrue({"not_refreshed", "unlimited", "ok"} <= produced)
        # unavailable / unsupported 不逐一列举（避免漏掉未来新状态）
        for status in produced - {"ok", "not_refreshed", "unlimited"}:
            self.lacks(f"status==='{status}'", self.body, status)
        # 兜底分支不渲染窗口表 → 不会显示空表/0%
        tail = self.body.split("status!=='ok'")[1]
        end = "Unavailable</span>`;"
        branch = tail[:tail.index(end) + len(end)]
        self.assertEqual(")return `<span class=\"unknown\" title=\"${esc(snapshot.error||'Usage unavailable')}\">"
                         "Unavailable</span>`;", branch)
        self.lacks_all(("usage-window", "metric(", "%"), branch, "unavailable branch")

    def test_ok_renders_each_window_name_and_percent(self):
        self.has("return (snapshot.windows||[]).map(item=>`<span class=\"usage-window\" "
                 "title=\"${esc(item.reset_at?`Resets ${item.reset_at}`:'Reset time unavailable')}\">"
                 "<b>${esc(item.name)}</b> ${item.percent==null?'Unknown':`${esc(item.percent)}%`}</span>`)"
                 ".join(' ')||metric(snapshot.percent==null?null:`${snapshot.percent}%`);", self.body)
        # UI 读取的字段必须是 M004 `_window()` 真实产出的字段
        window = re.search(r"def _window\(name: str.*?return (\{.*?\})\n", self.service, re.S).group(1)
        self.assertEqual(WINDOW_FIELDS, set(re.findall(r'"(\w+)":', window)))
        for field in ("item.name", "item.percent", "item.reset_at"):
            self.has(field, self.body, field)

    def test_unknown_percent_is_never_rendered_as_zero(self):
        self.has("${item.percent==null?'Unknown':`${esc(item.percent)}%`}", self.body)
        self.has("metric(snapshot.percent==null?null:`${snapshot.percent}%`)", self.body)
        # metric(null) → Unknown 样式（绝不显示 0）
        self.has("const metric=value=>value==null?'<span class=\"unknown\">Unknown</span>'"
                 ":`<span class=\"metric\">${esc(value)}</span>`;", self.js)
        # M004 侧 percent 可以合法为 None（_window 不做 0 归一）
        self.has('return {"name": name, "used": used, "quota": quota, '
                 '"remaining": quota - used if used is not None and quota is not None else None, '
                 '"percent": percent, "reset_at": reset_at}', self.service)
        self.lacks("||0", self.body)
        self.lacks("?? 0", self.body)

    def test_only_the_head_record_version_is_rendered_so_rows_replace(self):
        usage_view = assets.function_body(self.js, "loadUsage")
        self.has("api('/v1/usage?'+windowQuery())", usage_view)
        self.has("page.data.map(item=>", usage_view)
        # M003 只冻结 head 版本（同一 request_id 的 v1/v2 不累计）
        self.has("JOIN usage_record_versions v ON v.principal_id=h.principal_id AND v.request_id=h.request_id "
                 "AND v.record_version=h.head_record_version", assets.usage_py())
        self.has("head_record_version INTEGER NOT NULL", (assets.SRC_ROOT / "util/migrations/001_initial.sql")
                 .read_text(encoding="utf-8"))
        # 展示的是 record_version 事实（unknown → Unknown，不补零）
        self.has("statusMarkup(item.measurement_status,item.measurement_status==='measured'?'ok':'warn')", usage_view)
        for field in ("input_tokens", "output_tokens", "total_tokens"):
            self.has("${item.%s??'Unknown'}" % field, usage_view, field)

    def test_store_failure_keeps_the_last_table_and_marks_the_view_stale(self):
        usage_view = assets.function_body(self.js, "loadUsage")
        self.assertIn("catch(", usage_view)
        catch = usage_view[usage_view.rindex("catch("):]
        self.assertEqual("catch(error){reportLoadFailure(error)}", catch.strip())
        # 失败分支不重写 #usage-body → 保留上一屏表格，不显示空表
        self.lacks_all(("#usage-body", ".innerHTML", "'No records'"), catch, "loadUsage catch")
        # 503 由 api() → dispatchUiError(503) 标 stale，再由 reportLoadFailure 抑制重复提示
        self.assertIn("if(error.status===503)", assets.function_body(self.js, "dispatchUiError"))
        self.assertIn("[401,403,409,412,429,503].includes(error.status)", assets.function_body(self.js, "reportLoadFailure"))
        # 成功路径清 stale（T-UI-05 Stale → Loading → normal）
        self.has("clearStale()", usage_view)


class MTUI005RealSnapshotStates(PerTestLoopbackEnv):
    """M004 真实产出的快照状态逐个落进 `usageSummary` 的不同分支（ENV-2 loopback）。

    初态/状态切换全部经公开入口（PATCH provider 用量配置 + GET|POST 账号用量），
    不直写库；`local` 与 `minimax(无凭据)` 两条路径都不触外网。
    """

    def _provider(self):
        return self.request("GET", "/v1/providers")[1]["data"][0]

    def _set_usage_provider(self, usage_provider):
        provider = self._provider()
        body = {"name": provider["name"], "kind": provider["kind"], "endpoint": provider["endpoint"],
                "enabled": provider["enabled"],
                "usage": {"usage_provider": usage_provider, "max_concurrent_requests": 1,
                          "min_request_interval_ms": 0, "requests_per_minute": 0}}
        status, _, _ = self.request("PATCH", f"/v1/providers/{provider['id']}", body,
                                    headers={"If-Match": f'"{provider["id"]}.v{provider["version"]}"'})
        self.assertEqual(200, status)
        return provider["id"]

    def test_the_three_real_snapshots_hit_three_different_render_branches(self):
        provider_id = self._provider()["id"]
        # ① 未刷新：GET 只读库，从不触网
        first = self.request("GET", f"/v1/providers/{provider_id}/usage")[1]
        self.assertEqual("not_refreshed", first["status"])
        self.assertEqual([], first["windows"])
        # ② unavailable：切到 minimax 且无凭据（服务端不触网即收口）
        self._set_usage_provider("minimax")
        unavailable = self.request("GET", f"/v1/providers/{provider_id}/usage")[1]
        self.assertEqual("unavailable", unavailable["status"])
        self.assertEqual("credentials_missing", unavailable["source"])
        # error 非空 → UI 的 title 提示有内容（不是占位串）
        self.assertTrue(unavailable["error"])
        # ③ unlimited：local provider 的确认刷新（不触网）
        self._set_usage_provider("local")
        status, unlimited, _ = self.request("POST", f"/v1/providers/{provider_id}/usage",
                                            {"confirm_external_call": True})
        self.assertEqual(200, status)
        self.assertEqual("unlimited", unlimited["status"])
        # 三个真实状态互不相同 → 必须走三个不同分支
        self.assertEqual({"not_refreshed", "unavailable", "unlimited"},
                         {first["status"], unavailable["status"], unlimited["status"]})
        body = assets.function_body(assets.app_js(), "usageSummary")
        enumerated = set(re.findall(r"status==='([a-z_]+)'", body))
        self.assertEqual({"not_refreshed", "unlimited"}, enumerated)
        self.assertIn("snapshot.status!=='ok'", body)
        # unavailable 走兜底「非 ok 即 Unavailable」，与两个显式分支不同
        self.assertIn("unavailable", {first["status"], unavailable["status"], unlimited["status"]} - enumerated)

    def test_no_window_is_rendered_for_any_snapshot_without_windows(self):
        provider_id = self._provider()["id"]
        snapshot = self.request("GET", f"/v1/providers/{provider_id}/usage")[1]
        # 兜底分支之前的所有分支都不渲染 window：空 windows 不会产生空表
        body = assets.function_body(assets.app_js(), "usageSummary")
        head = body[:body.index("snapshot.status!=='ok'")]
        self.assertNotIn("usage-window", head)
        # ok 但 windows 为空 → 退到整体 percent，percent 为 null → Unknown（不显示 0%）
        self.assertEqual([], snapshot["windows"])
        self.assertIsNone(snapshot["percent"])
        self.assertIn("metric(snapshot.percent==null?null:`${snapshot.percent}%`)", body)


if __name__ == "__main__":
    unittest.main()

