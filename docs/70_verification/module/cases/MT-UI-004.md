<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-UI-004 — 状态映射分支（`backendState`/`tierState`）

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-UI-004` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-10-02` |
| Last Modified Date | `2026-10-02` |
| Template ID | `tests.module-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/module/cases/MT-UI-004.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-UI-004`）；责任摘要、分类与优先级以 [模块测试方案 §3](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-UI-004.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-UI-004` / M002 状态映射分支：`backendState`/`tierState` 的 Disabled/Unknown/Empty/Running/Idle（组装契约） v0.1.0-draft.2 / VRC-UI-001（web-ui-design §14 / web-ui.isd §9.1，web-ui 0.1.0-draft.2） / VRC-UI-001 / normal / P1（[方案清单 §3](../llmtier-module-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：组装后真实调用 + 等价类划分 + 分支覆盖（主要手段：无边界替身，全真实（仅 ENV-1/ENV-2 真实实现与真实静态产物））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M002-backendState/tierState 五态
- 要测什么（责任展开）：provider-disabled→Disabled 优先；availability 缺失→Unknown≠Idle；空 tier→Empty；healthy+running→Running/Idle（本 Case 责任：两映射函数分支全覆盖；Disabled 优先、Unknown≠Idle；映射读取字段在真实响应中存在）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝web-ui 组装后后端/层级状态映射分支与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/web_ui/app.js::backendState`/`tierState`、服务端 health/availability 字段

```text
backendState(deployment, provider, runtime) -> [label, tone]; tierState(tier) -> [label, tone]
```

- 初态构造（经公开入口）：真实静态产物 + ENV-2（`/v1/deployments`、`/v1/service-levels`、`/v1/runtime`、`/readyz` 字段实证）
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-2
- 依赖的测试资产（tests.asset-design 文档）：无（真实静态产物 `src/web_ui/*` + ENV-1/ENV-2 真实端点；不经替身）

## 3. 输入构造

- 逐参数输入构造：provider `enabled=false`；deployment `enabled=false`；health ∈ {healthy, unhealthy, unknown, running, probing, exhausted, unreachable}；`runtime.running>0`；tier `enabled=false`/`deployment_ids=[]`；availability ∈ {available, degraded, unavailable, 缺失}
- 边界/非法取值及理由：provider 禁用→`Disabled` 优先于 deployment 暂停；health unknown→`Unknown`（≠`Idle`）；healthy+`running>0`→`Running`，否则 `Idle`；tier 禁用→`Disabled`；无成员→`Empty`；availability available→`Ready`、degraded→`Attention`、unavailable→`Unreachable`、缺失→`Unknown`；映射读取的每个字段在真实响应中存在且类型正确
- 规模 / 时间域（数量、分页、复杂度、观测开销）：10 个测试方法；静态 + 4 次 loopback；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `backendState` 七分支 | 标签与语气逐条断言（无写点的取值只做静态断言，见 §4 `O-UI-HEALTHDOMAIN-1`） |
| 2 | `tierState` 五分支 | `Disabled`/`Empty`/`Ready`/`Attention`/`Unreachable`/`Unknown` |
| 3 | 优先级 | provider 禁用→`Disabled`（即使 health healthy） |
| 4 | Unknown≠Idle | availability 缺失→`Unknown` 而非 `Idle` |
| 5 | 字段存在性 | 映射读取字段均在真实响应中存在、类型匹配 |
| 6 | health 写点域 | 产品可写 health 值全部被映射覆盖 |
| 7 | availability 落点 | 真实 `/readyz` 的 availability 必落某分支 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：web-ui 模块设计 §14.1 + M001/M004 字段契约；按 `app.js` 两个映射函数逐分支与真实响应字段人工推导
- 互斥预期（成功 / 各错误分支）：五/七分支全覆盖；优先级与 Unknown≠Idle 成立；字段契约对齐

## 6. 错误路径、副作用与清理

- 错误出口与表现：无（本 Case 为契约断言）
- 副作用断言与清理：只读映射，不改状态

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-UI-004.py`（10 个）：`test_backend_state_disabled_wins_over_paused`、`test_backend_state_healthy_maps_running_or_idle_by_runtime_count`、`test_backend_state_unknown_is_not_idle`、`test_backend_state_probe_and_exhausted_are_warn_tone`、`test_tier_state_disabled_then_empty_then_availability`、`test_tier_state_never_derives_from_member_health_or_runtime`、`test_every_state_label_has_a_distinct_icon`、`test_every_field_the_two_mappings_read_is_present_in_the_real_responses`、`test_observed_availability_always_lands_in_a_tier_state_branch`、`test_health_values_the_product_can_write_are_all_covered_by_the_mapping`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-UI-004.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
