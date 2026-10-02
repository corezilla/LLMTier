"""MT-UI-001 — 组装后 5 页装载与状态语义映射（M002 web-ui，层①，normal，P1）。

覆盖：`index.html` 的 5 页 / 2 抽屉容器契约、`app.js` 导航接线与 DOM 容器
契约（app.js 写入的每个容器都真实存在于 index.html）、Tier 状态的**单一
数据源**（只取 `/readyz.models[].availability`，不从成员聚合）、`readyz`
三态映射、Unknown≠Idle / Disabled 优先 / 空态的渲染分支。

环境：**真实静态产物契约层**（读 `src/web_ui/index.html`、`app.js`、
`icons.svg` 文本，即 M001 `_static` 交付的同一目录；无 JS 执行、无网络、
无上游）。真实浏览器行为级归系统层 `ST-UI-*`。
"""
from __future__ import annotations

import re
import unittest

from tests.module.cases.support import web_assets as assets

PAGES = ("home", "providers", "stats", "logs", "diagnostics")
PAGE_TITLES = {"home": "Home", "providers": "Providers", "stats": "Stats", "logs": "Logs",
               "diagnostics": "Diagnostics"}
LOADERS = {"home": "loadHome()", "providers": "loadProviders()", "stats": "loadStats()",
           "logs": "loadUsage()", "diagnostics": "loadDiagnostics()"}
# Logs 页 3 个子表 → 装载器 / 容器
LOG_SUBTABS = {"usage": ("loadUsage", "usage-body"), "audit": ("loadAudit", "audit-body"),
               "events": ("loadLogs", "log-body")}
EMPTY_STATES = ("No tiers configured", "No providers configured", "No models available.",
                "No calls recorded in this window.", "No records", "No snapshots",
                "No stats", "No traces", "No injections")
# 空态只允许出现在渲染分支，不允许出现在失败兜底里
RENDERERS = ("loadHome", "loadUsage", "loadAudit", "loadLogs", "loadStats", "renderTree",
             "renderProviders", "loadSnapshots", "loadDiagStats", "loadTraces", "loadInjections")


class MTUI001PageAssembly(unittest.TestCase):
    def test_index_delivers_five_pages_and_two_drawers(self):
        html = assets.index_html()
        self.assertEqual(set(PAGES), set(re.findall(r'<section id="([a-z]+)" class="page', html)))
        self.assertEqual(set(PAGES), set(re.findall(r'data-page="([a-z]+)"', html)))
        self.assertEqual(1, html.count('class="page active"'))
        self.assertEqual({"provider-mask", "tier-mask"}, set(re.findall(r'<div id="([a-z-]+-mask)"', html)))
        self.assertEqual(set(PAGES), set(assets.dom_ids()) & set(PAGES))

    def test_nav_handler_wires_every_page_to_its_loader_and_title(self):
        js = assets.app_js()
        self.assertIn("$$('nav button').forEach", js)
        for page in PAGES:
            self.assertIn(f"{page}:['{PAGE_TITLES[page]}',", js, page)
            self.assertIn(f"button.dataset.page==='{page}'", js, page)
        for loader in set(LOADERS.values()):
            self.assertIn(loader, js)
        # 切页只做 class 切换 + 触发装载；不直接写业务容器
        self.assertIn("$$('.page').forEach", js)
        self.assertIn("$('#'+button.dataset.page).classList.add('active')", js)

    def test_every_container_app_js_writes_into_exists_in_index_html(self):
        targets = assets.dom_write_targets()
        self.assertNotEqual(set(), targets)
        self.assertEqual(set(), targets - assets.dom_ids())
        # app.js 引用的 icon sprite 与 index.html 引用的必须是同一份真实资产
        symbols = assets.icon_symbols()
        referenced = set(re.findall(r"iconSvg\('([a-z0-9-]+)'\)", assets.app_js()))
        referenced |= set(re.findall(r"iconButton\('([a-z0-9-]+)'", assets.app_js()))
        referenced |= set(assets.status_icon_map().values()) | {assets.status_icon_default()}
        referenced |= set(re.findall(r'#icon-([a-z0-9-]+)', assets.index_html()))
        pause_play = re.search(r"const toggleName=deployment\.enabled\?'([a-z0-9-]+)':'([a-z0-9-]+)'", assets.app_js())
        self.assertIsNotNone(pause_play)
        referenced |= {pause_play.group(1), pause_play.group(2)}
        self.assertEqual(set(), referenced - symbols)

    def test_tier_state_has_a_single_data_source_readyz_availability(self):
        js = assets.app_js()
        home = assets.function_body(js, "loadHome")
        # `tierAvailability` 只在 loadHome 里从 /readyz 写入一次
        self.assertEqual(1, len(re.findall(r"state\.tierAvailability=", js)))
        self.assertIn("state.tierAvailability=Object.fromEntries((ready.models||[]).map(item=>[item.id,item.availability]))", home)
        self.assertIn("fetch('/readyz'", home)
        tier_state = assets.function_body(js, "tierState")
        self.assertIn("const availability=state.tierAvailability[tier.id];", tier_state)
        # 不从成员聚合：tierState 不读成员 health，也不读成员列表
        # （`tier.deployment_ids.length` 只用于 Empty 判定，不参与状态推导）
        self.assertNotIn("health", tier_state)
        self.assertNotIn("state.deployments", tier_state)

    def test_readyz_status_maps_to_gateway_chip_tier_count_and_healthz_version(self):
        home = assets.function_body(assets.app_js(), "loadHome")
        self.assertIn("const gateway=ready.status==='ready'?'Ready':ready.status==='degraded'?'Degraded':'Not ready';", home)
        self.assertIn("const available=(ready.models||[]).filter(item=>item.availability==='available').length;", home)
        self.assertIn("$('#tier-summary').textContent=`Tiers ${available}/${state.tiers.length}`;", home)
        self.assertIn("api('/healthz')", home)
        self.assertIn("$('#build-meta').textContent=`Version ${health.version}", home)
        # /readyz 的三态来源是 M001 health_view / readiness_view
        self.assertIn('path == "/readyz" and method == "GET"', assets.app_py())
        self.assertIn('path == "/healthz" and method == "GET"', assets.app_py())
        self.assertIn('"availability": availability', assets.health_py())
        self.assertIn('status = "ready" if all(m["availability"] == "available" for m in models)', assets.health_py())

    def test_disabled_wins_and_unknown_is_not_idle(self):
        body = assets.function_body(assets.app_js(), "backendState")
        disabled_at = body.index("if(!provider?.enabled)return ['Disabled','muted'];")
        paused_at = body.index("if(!deployment.enabled)return ['Paused','muted'];")
        self.assertLess(disabled_at, paused_at)
        icons = assets.status_icon_map()
        self.assertEqual("circle-off", icons["Disabled"])
        self.assertEqual("circle-pause", icons["Paused"])
        self.assertEqual("circle-dot", icons["Idle"])
        self.assertEqual("circle-help", assets.status_icon_default())
        # Unknown 走兜底图标，与 Idle/Disabled 的图标互不相同 → 视觉上不可混淆
        self.assertNotIn("Unknown", icons)
        self.assertEqual(3, len({icons["Disabled"], icons["Idle"], assets.status_icon_default()}))

    def test_empty_states_are_present_for_tier_provider_and_stats(self):
        js = assets.app_js()
        for text in EMPTY_STATES:
            self.assertIn(text, js, text)
        # 空态 ≠ 加载失败：装载失败走 reportLoadFailure（stale），空态是正常渲染分支
        tree = assets.function_body(js, "renderTree")
        self.assertIn("'<div class=\"empty\">No tiers configured</div>'", tree)
        self.assertIn("'<div class=\"empty\">No providers configured</div>'", assets.function_body(js, "renderProviders"))
        self.assertNotIn("reportLoadFailure", tree)
        # 任一渲染函数的 catch 兜底里都不得写空态（失败不得覆盖成空洞）
        for name in RENDERERS:
            body = assets.function_body(js, name)
            if "catch(" not in body:
                continue
            catch = body[body.rindex("catch("):]
            for text in EMPTY_STATES:
                self.assertNotIn(text, catch, f"{name} catch")
        # 状态标签 → 图标映射覆盖 backendState / tierState 产出的全部标签
        icons = assets.status_icon_map()
        for label in ("Disabled", "Paused", "Running", "Idle", "Probing", "Exhausted", "Unreachable",
                      "Empty", "Ready", "Attention", "Degraded", "Not ready"):
            self.assertIn(label, icons, label)

    def test_bootstrap_loads_home_as_the_first_paint_of_the_delivered_page(self):
        html = assets.index_html()
        js = assets.app_js()
        # 交付形态：index.html 在 body 末尾以真实 <script src> 引入 /ui/app.js
        self.assertIn('<script src="/ui/app.js"></script>', html)
        self.assertNotIn("<script>", html)
        # 脚本最后一条语句即首次装载入口（无用户操作也能出首屏）
        self.assertEqual("loadHome();", js.rstrip().splitlines()[-1])
        # 首屏装载器就是 nav 的 home 装载器（同一函数，单一入口）
        self.assertIn("if(button.dataset.page==='home')loadHome();", js)
        # 交付态与初始 active 标记一致：home 页与 Home 按钮初始为 active，其余页惰性装载
        self.assertIn('<button class="active" data-page="home">', html)
        self.assertEqual(1, html.count('class="page active"'))
        # Home 容器在交付态即为占位而非空态：首次装载失败才由 reportLoadFailure 标 stale
        self.assertIn('<div id="tree" class="tree empty">Loading…</div>', html)
        self.assertIn("}catch(error){reportLoadFailure(error)}", assets.function_body(js, "loadHome"))

    def test_logs_subtabs_and_diagnostics_page_are_wired_to_their_loaders(self):
        html = assets.index_html()
        js = assets.app_js()
        # Logs 页 3 个子表：按钮 data-tab、容器 .sub、装载器与落点 tbody 三者一一对应
        self.assertEqual(set(LOG_SUBTABS), set(re.findall(r'data-tab="([a-z]+)"', html)))
        self.assertEqual(set(LOG_SUBTABS), set(re.findall(r'<div id="([a-z]+)" class="sub', html)))
        handler = js[js.index("$$('[data-tab]')"):]
        for tab, (loader, node) in LOG_SUBTABS.items():
            self.assertIn(f"if(button.dataset.tab==='{tab}'){loader}()", handler, tab)
            body = assets.function_body(js, loader)
            self.assertIn(f"$('#{node}').innerHTML", body, tab)
            self.assertIn(node, assets.dom_ids(), tab)
        # nav 进入 logs 一次装载三张表
        self.assertIn("if(button.dataset.page==='logs'){loadUsage();loadAudit();loadLogs();}", js)
        # 诊断页先装 registry 再装诊断：注入选择器读 state.deployments，顺序不可换
        self.assertIn("if(button.dataset.page==='diagnostics'){loadRegistry().then(()=>loadDiagnostics());}", js)
        registry = assets.function_body(js, "loadRegistry")
        self.assertIn("api('/v1/providers'),api('/v1/deployments'),api('/v1/service-levels'),api('/v1/runtime')", registry)
        self.assertIn("state={...state,providers:providers.data,deployments:deployments.data,"
                      "tiers:tiers.data,runtime}", registry)
        self.assertIn("state.deployments||[]", assets.function_body(js, "diagDeployments"))
        # 统计页的两组维度（tier/deployment × 24h/7d/today/all）驱动唯一装载器
        self.assertEqual({"tier", "deployment"}, set(re.findall(r'data-group="([a-z]+)"', html)))
        self.assertEqual({"24h", "7d", "today", "all"}, set(re.findall(r'data-range="([a-z0-9]+)"', html)))
        self.assertIn("statsState.group_by=button.dataset.group;loadStats();", js)
        self.assertIn("statsState.range=button.dataset.range;loadStats();", js)
        self.assertIn("&group_by=${group}", assets.function_body(js, "loadStats"))


if __name__ == "__main__":
    unittest.main()
