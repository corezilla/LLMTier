<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-UI-001 — 组装后页面装载与状态语义契约

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-UI-001` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-UI-001.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-UI-001`）；责任摘要、分类与优先级以 [模块测试方案 §3](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-UI-001.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-UI-001` / M002 web-ui §9 · 页面装载（组装静态产物） v0.1.0-draft.2 / VRC-UI-001（web-ui-design §14 / web-ui.isd §9.1，web-ui 0.1.0-draft.2） / VRC-UI-001 / normal / P1（[方案清单 §3](../llmtier-module-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：组装后真实调用 + 等价类划分 + 分支覆盖（主要手段：无边界替身，全真实（仅 ENV-1/ENV-2 真实实现与真实静态产物））
- **覆盖的分支 / 组合 / 迁移 ID**：无（层① 接口行为分母行）
- 要测什么（责任展开）：组装后 5 页装载与 tier/成员状态语义映射（Unknown≠Idle、Disabled 优先、空态）、`readyz` 映射、单一数据源（本 Case 责任：5 页 + 2 抽屉装载链完整；DOM 写目标齐全；`readyz`/tier/backend 状态映射语义成立；空态与失败态不混淆）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝web-ui 组装后五页装载链与状态语义与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/web_ui/index.html`（5 页容器 + 抽屉）、`src/web_ui/app.js`（`tierState`/`backendState`/`loadHome`/nav 绑定）

```text
静态产物契约：index.html 5 页 + 2 抽屉；app.js 装载入口与状态映射
```

- 初态构造（经公开入口）：真实静态产物（`src/web_ui/*`）+ ENV-2 loopback（`/ui/` 交付与首屏 API 交叉核对）
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-2（loopback 交付）+ ENV-1（`/readyz` 等端点）
- 依赖的测试资产（tests.asset-design 文档）：无（真实静态产物 `src/web_ui/*` + ENV-1/ENV-2 真实端点；不经替身）

## 3. 输入构造

- 逐参数输入构造：`/ui/`、`/ui/app.js` 交付文本；5 个 `data-page`；2 个抽屉；`state` 单一数据源；`readyz`→gateway chip/tier 计数映射；Disabled 优先与 Unknown≠Idle；9 条空态串
- 边界/非法取值及理由：5 页与 2 抽屉齐全；`app.js` 末行 `loadHome()` 为首屏入口且交付态 `home` 为 active；每个 DOM 写目标在 `index.html` 存在；`readyz` 四态映射；provider 禁用优先于 health；availability 缺失→Unknown（≠Idle）；空态串在各渲染面成对出现且不与失败路径混用
- 规模 / 时间域（数量、分页、复杂度、观测开销）：9 个测试方法；静态文本 + 6 次 loopback 请求；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `/ui/` 与 `/ui/app.js` 交付 | index 含 5 页容器 + 2 抽屉；app.js 含 `dispatchUiError` |
| 2 | nav 绑定 | 5 个 `data-page` 各有 loader/标题/副标题绑定 |
| 3 | DOM 写目标存在性 | app.js 写入的每个选择器在 index.html 有对应元素 |
| 4 | tier/成员状态映射 | `Disabled` 优先；availability 缺失→`Unknown`（≠`Idle`）；`readyz` 状态→gateway chip 与 tier 计数 |
| 5 | 空态串 | 9 条空态串成对出现；渲染函数 catch 分支不含空态串 |
| 6 | 首屏装载 | `index.html` 交付 `<script src="/ui/app.js">`；app.js 末行调 `loadHome()`；交付态 home 为 active |
| 7 | Logs 页子结构 | 3 个 `data-tab` ↔ `.sub` ↔ loader ↔ tbody 四方对应；诊断页装载顺序（`loadRegistry().then(loadDiagnostics)`） |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：web-ui 模块设计 §14.1 + ISD 页面契约；按 `index.html`/`app.js` 真实文本逐项人工推导（行为级真实 JS 执行归系统层 `ST-UI-*`）
- 互斥预期（成功 / 各错误分支）：5 页装载链与状态语义映射成立；DOM 目标齐全；空态/失败态不混淆

## 6. 错误路径、副作用与清理

- 错误出口与表现：无（本 Case 为契约断言）
- 副作用断言与清理：只读静态产物与端点，不改状态

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-UI-001.py`（9 个）：`test_index_delivers_five_pages_and_two_drawers`、`test_nav_handler_wires_every_page_to_its_loader_and_title`、`test_every_container_app_js_writes_into_exists_in_index_html`、`test_tier_state_has_a_single_data_source_readyz_availability`、`test_readyz_status_maps_to_gateway_chip_tier_count_and_healthz_version`、`test_disabled_wins_and_unknown_is_not_idle`、`test_empty_states_are_present_for_tier_provider_and_stats`、`test_bootstrap_loads_home_as_the_first_paint_of_the_delivered_page`、`test_logs_subtabs_and_diagnostics_page_are_wired_to_their_loaders`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-UI-001.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
