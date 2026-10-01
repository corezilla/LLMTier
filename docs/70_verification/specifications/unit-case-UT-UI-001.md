<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-UI-001 — 页面加载、tier/成员状态与 readyz 映射

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-UI-001` |
| Document Version | `0.1.0-draft.2` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-30` |
| Last Modified Date | `2026-10-01` |
| Template ID | `tests.unit-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/specifications/unit-case-UT-UI-001.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-UI-001`）；责任摘要、分类与优先级以 [单元测试方案 §3](../schemes/llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [web-ui-design.md](../../40_module_design/web-ui-design.md) §14 / ISD [web-ui.isd.md](../../50_implementation_design/web-ui.isd.md) §9.1，设计验证项 `VRC-UI-001`（固定版本 `web-ui 0.1.0-draft.2`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `UI`；裁剪依据见 [STD 裁剪清单](../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-UI-001` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-UI-001` / `VRC-UI-001`（web-ui 模块设计 §14 / web-ui-isd §9.1，web-ui 0.1.0-draft.2） / `VRC-UI-001` / normal / P1（[方案清单 §3](../schemes/llmtier-unit-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：等价类划分（合法状态→标签映射）
- 要测什么（责任展开）：被测：`src/web_ui/index.html`/`app.js` 的 5 页结构、Home 默认页、tier 树目标、成员/后端状态来源独立、`readyz` 映射、图标 sprite 完整、无 Bearer 存储。
- 明确不测什么 / 失败含义：本 Case 只做源码字符串契约（快速下位防线）；**真实浏览器渲染/交互归系统层 `UIT-UI-001..010`（`tests/ui/`，headless Chrome over CDP，已关闭 `RISK-UI-EXEC-1`）**；不测后端行为。失败含义＝UI 契约/状态语义实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/web_ui/index.html`、`src/web_ui/app.js`、`src/web_ui/icons.svg`（文本契约）

```text
静态契约断言：`index.html`/`app.js`/`icons.svg` 内容
```

- 初态构造（经公开入口）：无需运行时；`@classmethod setUpClass` 直接读取真实文件
- Fixture / 向量及版本：`tests/unit/v03/test_webui_contract.py::setUpClass`
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../plans/llmtier-unit-test-plan.md) 分配）：ENV-1 隔离 Python 临时库 / ENV-2 loopback 测试 HTTP 实例 / ENV-3 provider 进程内 fake（按 Case 需要，见 §4）
- 依赖的测试资产（tests.asset-design 文档）：无（真实产物）

## 3. 输入构造

- 逐参数输入构造：真实 `index.html`/`app.js`/`icons.svg` 文本
- 边界/非法取值及理由：页面数量=5、默认 active 页、状态来源独立
- 规模 / 时间域（数量、分页、复杂度、观测开销）：单文件读取，O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 读取 UI 三文件 | 文本 |
| 2 | 断言 5 页与 Home 默认 | `class="page` 计数、`id="home" class="page active"` |
| 3 | 断言 tier 树与成员/后端状态来源独立 | `id="tree"`、来源 id 不重叠 |
| 4 | 断言图标 sprite 与无 localStorage/Bearer | sprite token、`localStorage` 缺席 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：web-ui 设计 §5/§9 的 UI 契约；人工枚举 token，不调用被测复算。**判据语义以设计验证项 `VRC-UI-001` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：5 个 `class="page`；Home 默认 active；`#tree` 存在；状态来源独立；sprite 完整；`app.js` 不含 `localStorage`/`Bearer `

## 6. 错误路径、副作用与清理

- 错误出口与表现：无（静态契约无错误出口）
- 副作用断言与清理：只读文件；无清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/v03/test_webui_contract.py::test_five_pages/test_home_is_default/test_fixed_tier_tree_target/test_tree_has_no_column_title_row/test_tier_and_member_status_sources_are_independent/test_approved_icon_sprite_is_complete/test_no_bearer_storage`（注意：本 Case 的测试函数当前按子句（test case method）映射；若与设计 VRC 不一致，以设计修订回溯后重裁）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/v03/test_webui_contract.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit/v03`）；执行状态与 Verdict 归 Run 报告（当前无录制 Run，见方案 §4 G-UT-1）。

