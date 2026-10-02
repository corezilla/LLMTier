"""MT-UI-004 — 状态映射分支 `backendState`/`tierState`（M002 web-ui，层②，normal，P1）。

覆盖五个状态分支的判定顺序与取值：provider 禁用→Disabled **优先**于
Deployment 暂停；health 缺失/未识别→Unknown（≠Idle）；tier 无成员→Empty；
availability available/degraded/unavailable→Ready/Attention/Unreachable；
healthy + `running>0`→Running、healthy + `running=0`→Idle。每个标签在
`statusIconName` 里有互不相同的图标（视觉上不可混淆）；并用 ENV-2 真实
loopback 验证两个映射函数读取的字段与取值域就是后端真实返回的形状。

环境：**真实静态产物契约层 + ENV-2 loopback**（读 `src/web_ui/app.js` /
`icons.svg` 文本，并在 127.0.0.1:0 上取真实 `/v1/deployments`、
`/v1/service-levels`、`/v1/runtime`、`/readyz` 响应比对；无 JS 执行、不经
LAN、不触上游）。真实浏览器行为级归系统层 `ST-UI-*`。
"""
from __future__ import annotations

import re
import unittest

from tests.module.cases.support import web_assets as assets
from tests.module.cases.support.http_env import PerTestLoopbackEnv

BACKEND_LABELS = ("Disabled", "Paused", "Running", "Idle", "Probing", "Exhausted", "Unreachable")
TIER_LABELS = ("Disabled", "Empty", "Ready", "Attention", "Unreachable")
TONES = ("ok", "warn", "bad", "muted")


class MTUI004StateMapping(assets.SourceContractMixin, unittest.TestCase):
    def setUp(self):
        self.js = assets.app_js()
        self.backend = assets.function_body(self.js, "backendState")
        self.tier = assets.function_body(self.js, "tierState")
        self.icons = assets.status_icon_map()

    def test_backend_state_disabled_wins_over_paused(self):
        disabled = "if(!provider?.enabled)return ['Disabled','muted'];"
        paused = "if(!deployment.enabled)return ['Paused','muted'];"
        self.assertIn(disabled, self.backend)
        self.assertIn(paused, self.backend)
        # 优先级：provider 禁用先判；即便 Deployment 仍标 enabled 也显示 Disabled
        self.assertLess(self.backend.index(disabled), self.backend.index(paused))
        # 两者都是 muted（非故障色），与 health 故障态区分
        self.assertEqual("circle-off", self.icons["Disabled"])
        self.assertEqual("circle-pause", self.icons["Paused"])
        self.assertNotEqual(self.icons["Disabled"], self.icons["Unreachable"])

    def test_backend_state_healthy_maps_running_or_idle_by_runtime_count(self):
        self.has("if(value==='healthy'||value==='running')"
                 "return [(runtime.running||0)>0?'Running':'Idle','ok'];", self.backend)
        # 判定依据是 runtime.running（准入面事实），不是 health 文案
        self.has("String(deployment.health||'unknown').toLowerCase()", self.backend)
        self.assertEqual("activity", self.icons["Running"])
        self.assertEqual("circle-dot", self.icons["Idle"])
        # runtime 面缺失时 `running||0` → Idle（保守：不误报 Running）
        self.has("const value=String(deployment.health||'unknown').toLowerCase();", self.backend)
        # M001 的 /v1/runtime 确实提供 running/max_concurrent
        self.has("return self._json(200, app.router.snapshot())", assets.app_py())
        self.has('"running": int(self._inflight[row["deployment_id"]])', assets.routing_py())

    def test_backend_state_unknown_is_not_idle(self):
        # health 缺省为 'unknown'；backendState 未识别 'unknown' → 落到兜底 Unknown（不是 Idle）
        self.has("const value=String(deployment.health||'unknown').toLowerCase();", self.backend)
        self.lacks("value==='unknown'", self.backend)
        recognized = re.findall(r"value==='([a-z]+)'", self.backend)
        self.assertEqual(["healthy", "running", "probing", "exhausted", "unhealthy", "unreachable"], recognized)
        self.assertNotIn("unknown", recognized)
        self.assertTrue(self.backend.rstrip().endswith("return ['Unknown','muted'];"))
        # M001/M004 侧的 deployment health 初值就是 unknown（新建未探测）
        self.has('"unknown"', assets.registry_py())
        # Unknown 走 statusIconName 兜底图标，与 Idle/Disabled/Empty 全部不同
        fallback = assets.status_icon_default()
        self.assertNotIn("Unknown", self.icons)
        self.assertEqual(4, len({fallback, self.icons["Idle"], self.icons["Disabled"], self.icons["Empty"]}))

    def test_backend_state_probe_and_exhausted_are_warn_tone(self):
        self.has("if(value==='probing')return ['Probing','warn'];", self.backend)
        self.has("if(value==='exhausted')return ['Exhausted','warn'];", self.backend)
        self.has("if(value==='unhealthy'||value==='unreachable')return ['Unreachable','bad'];", self.backend)
        self.assertEqual("scan-search", self.icons["Probing"])
        self.assertEqual("gauge", self.icons["Exhausted"])
        self.assertEqual("cloud-off", self.icons["Unreachable"])
        # 判定顺序：健康 → 探测中 → 配额耗尽 → 不健康
        order = [self.backend.index(needle) for needle in
                 ("'healthy'", "'probing'", "'exhausted'", "'unhealthy'")]
        self.assertEqual(sorted(order), order)

    def test_tier_state_disabled_then_empty_then_availability(self):
        self.assertEqual(["if(!tier.enabled)return ['Disabled','muted'];",
                          "if(!tier.deployment_ids.length)return ['Empty','muted'];",
                          "const availability=state.tierAvailability[tier.id];",
                          "if(availability==='available')return ['Ready','ok'];",
                          "if(availability==='degraded')return ['Attention','warn'];",
                          "if(availability==='unavailable')return ['Unreachable','bad'];",
                          "return ['Unknown','muted'];"],
                         [line.strip() for line in self.tier.strip().splitlines()])
        # 顺序：Disabled 优先于 Empty，Empty 优先于 availability
        self.assertLess(self.tier.index("!tier.enabled"), self.tier.index("!tier.deployment_ids.length"))
        self.assertLess(self.tier.index("!tier.deployment_ids.length"), self.tier.index("tierAvailability"))
        # 未列举的 availability（含缺失）→ Unknown
        self.assertTrue(self.tier.rstrip().endswith("return ['Unknown','muted'];"))
        for label, tone in (("Ready", "ok"), ("Attention", "warn"), ("Unreachable", "bad"),
                            ("Disabled", "muted"), ("Empty", "muted"), ("Unknown", "muted")):
            self.assertIn(f"['{label}','{tone}']", self.tier + "return ['Unknown','muted'];", label)

    def test_tier_state_never_derives_from_member_health_or_runtime(self):
        # RULE-UI-TIERSTATE：Tier 行只取 /readyz availability，不从成员聚合
        self.lacks_all(("health", "state.deployments", "runtime", "backendState"), self.tier, "tierState")
        # 成员行独立取 Deployment health/runtime（RULE-UI-TIERSTATE 的另一半）
        tree = assets.function_body(self.js, "renderTree")
        self.has("const overall=tierState(tier);", tree)
        self.has("const owner=provider(deployment.provider_id),status=backendState(deployment,owner,runtime);", tree)
        # Provider 行状态也走同一个 backendState（RULE-UI 复用）
        self.has("backendState(item,provider,state.runtime.deployments[item.id])[0]",
                 assets.function_body(self.js, "renderProviders"))

    def test_every_state_label_has_a_distinct_icon(self):
        labels = set(BACKEND_LABELS) | set(TIER_LABELS)
        for label in labels:
            self.assertIn(label, self.icons, label)
        # 语义互不相同的标签不得共用同一图标
        self.assertEqual(len(labels), len({self.icons[label] for label in labels}))
        # 网关状态（readyz 映射）复用同一图标表，Degraded 与 Attention 同为告警色
        self.assertEqual("triangle-alert", self.icons["Attention"])
        self.assertEqual(self.icons["Attention"], self.icons["Degraded"])
        self.assertEqual("triangle-alert", self.icons["Not ready"])
        self.assertEqual("circle-help", assets.status_icon_default())  # 未列举状态（Unknown）兜底
        # 图标必须是 icons.svg 里真实存在的 symbol
        self.assertEqual(set(), {self.icons[label] for label in labels} - assets.icon_symbols())
        # 状态标签经 statusMarkup 输出，并带 title/aria-label（可访问名 ≠ 颜色）
        self.has("const statusMarkup=(label,tone='muted')=>`<span class=\"status-icon ${tone}\" role=\"img\" "
                 "tabindex=\"0\" title=\"${esc(label)}\" aria-label=\"${esc(label)}\">", self.js)
        self.assertEqual(set(TONES),
                         set(re.findall(r"return \['[A-Za-z ]+','([a-z]+)'\]", self.backend + self.tier)))


class MTUI004StateMappingInputs(PerTestLoopbackEnv):
    """映射函数读取的字段与取值域 == 后端真实响应形状（ENV-2 loopback）。"""

    def test_every_field_the_two_mappings_read_is_present_in_the_real_responses(self):
        deployment = self.request("GET", "/v1/deployments")[1]["data"][0]
        for field in ("id", "name", "provider_id", "backend_model", "enabled", "health", "version"):
            self.assertIn(field, deployment)
        tier = next(item for item in self.request("GET", "/v1/service-levels")[1]["data"]
                    if item["id"] == "Worker")
        for field in ("id", "deployment_ids", "enabled", "version"):
            self.assertIn(field, tier)
        # 播种的 Worker 只有一个成员 → Empty 分支与 availability 分支互斥可判
        self.assertEqual([deployment["id"]], tier["deployment_ids"])
        self.assertTrue(tier["enabled"])
        runtime = self.request("GET", "/v1/runtime")[1]["deployments"][deployment["id"]]
        self.assertEqual({"running", "max_concurrent"}, set(runtime))
        self.assertIsInstance(runtime["running"], int)
        # provider 侧的 enabled（Disabled 优先分支的输入）
        provider = next(item for item in self.request("GET", "/v1/providers")[1]["data"]
                        if item["id"] == deployment["provider_id"])
        self.assertIn("enabled", provider)

    def test_observed_availability_always_lands_in_a_tier_state_branch(self):
        ready = self.request("GET", "/v1/runtime")[1]  # 保证路由栈已就绪
        self.assertIn("queues", ready)
        models = self.request("GET", "/readyz")[1]["models"]
        observed = {item["availability"] for item in models}
        # tierState 只枚举三个 availability 分支，其余落 Unknown
        self.assertTrue(observed <= {"available", "degraded", "unavailable"}, observed)
        self.assertIn("available", observed)  # Ready 分支真实可达
        branches = set(re.findall(r"availability==='([a-z]+)'",
                                  assets.function_body(assets.app_js(), "tierState")))
        self.assertEqual({"available", "degraded", "unavailable"}, branches)
        # M001 侧的可写域与 UI 分支域一致（readiness_view 只产出这三个字面量）
        health_source = assets.health_py()
        start = health_source.index("def readiness_view")
        readiness = health_source[start:health_source.index("\ndef ", start + 1)]
        self.assertEqual({"available", "degraded", "unavailable"},
                         set(re.findall(r'"(available|degraded|unavailable)"', readiness)))

    def test_health_values_the_product_can_write_are_all_covered_by_the_mapping(self):
        migration = (assets.SRC_ROOT / "util/migrations/001_initial.sql").read_text(encoding="utf-8")
        self.assertIn("health TEXT NOT NULL DEFAULT 'unknown'", migration)
        # health 的唯一写点：apply_probe_result（校验集）+ 唯一调用方 AdminService.probe
        validator = re.search(r'if status not in \{([^}]*)\}', assets.health_py()).group(1)
        self.assertEqual({"healthy", "degraded", "unhealthy", "unknown"},
                         set(re.findall(r'"(\w+)"', validator)))
        self.assertEqual([("healthy", "unhealthy")],
                         re.findall(r'"(\w+)" if adapter\.probe\(\) else "(\w+)"', assets.admin_py()))
        recognized = set(re.findall(r"value==='([a-z]+)'", assets.function_body(assets.app_js(), "backendState")))
        # 实际可写域 {unknown, healthy, unhealthy} 全部有显式分支或兜底分支
        self.assertTrue({"unknown", "healthy", "unhealthy"} <= recognized | {"unknown"})
        self.assertEqual({"healthy", "unhealthy"}, recognized & {"healthy", "unhealthy"})
        # 其余被识别的取值（running/probing/exhausted/unreachable）当前无写点，
        # 只能作为前向兼容分支存在——不对应任何后端事实，不在本层做行为断言
        self.assertEqual({"healthy", "running", "probing", "exhausted", "unhealthy", "unreachable"}, recognized)


if __name__ == "__main__":
    unittest.main()
