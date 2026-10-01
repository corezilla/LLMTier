<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-UI-008 — reportLoadFailure 保留上一屏并标 stale

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-UI-008` |
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
| Canonical Path | `docs/70_verification/unit/cases/UT-UI-008.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-UI-008`）；责任摘要、分类与优先级以 [单元测试方案 §3](../llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [web-ui](../../../40_module_design/web-ui-design.md) §14 / ISD [web-ui.isd.md](../../../50_implementation_design/web-ui.isd.md) §9.1，设计验证项 `VRC-UI-002`（固定版本 `web-ui 0.1.0-draft.2`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `web_ui`；裁剪依据见 [STD 裁剪清单](../../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-UI-008` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-UI-008` / M002 web-ui §14.2 · `reportLoadFailure` v0.1.0-draft.2 / `VRC-UI-002` / negative / P1（[方案清单 §3](../llmtier-unit-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（非列举状态保留上一屏）
- 要测什么（责任展开）：被测（字符串契约层）：非列举状态（网络/500）经 `reportLoadFailure` 保留上一屏并标 stale；与 `dispatchUiError` 分工（后者处理 401/403/409/412/429/503）。
- 明确不测什么 / 失败含义：不测：`app.js` 运行时行为（G-UT-3）；不测各 HTTP 错误的具体交互。失败含义＝load 失败降级分支源码契约缺失。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/web_ui/app.js` 的 `reportLoadFailure` 与 `dispatchUiError` 源片段

```text
function reportLoadFailure(error)  # 源码分支契约
```

- 初态构造（经公开入口）：读取真实 `src/web_ui/app.js` 文件文本
- Fixture / 向量及版本：`tests/unit/v03/test_webui_contract.py::WebUIBranchContractTests`
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../llmtier-unit-test-plan.md) 分配）：无（静态文件读取，真实产物）
- 依赖的测试资产（tests.asset-design 文档）：无（真实静态产物）

## 3. 输入构造

- 逐参数输入构造：`app.js` 源文本
- 边界/非法取值及理由：断言 `reportLoadFailure` 定义、列举状态集合、`markStale` 调用 token
- 规模 / 时间域（数量、分页、复杂度、观测开销）：单文件文本，O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 断言 `reportLoadFailure` 定义存在 | `function reportLoadFailure(error)` |
| 2 | 断言列举状态集合 | `[401,403,409,412,429,503].includes(error.status)` |
| 3 | 断言保留上一屏标记 | `markStale('Refresh failed — showing the last known data.')` |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：web-ui §14.2/T-UI-03 stale 语义 + 人工比对源码；字符串契约层。**判据语义以设计验证项 `VRC-UI-002` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：非列举状态走 `reportLoadFailure` 且 `markStale` 保留上一屏；列举状态留给 `dispatchUiError`；token 存在

## 6. 错误路径、副作用与清理

- 错误出口与表现：无运行时错误出口（静态断言）
- 副作用断言与清理：无（只读源代码）

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/v03/test_webui_contract.py::WebUIBranchContractTests::test_report_load_failure_keeps_last_screen`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/v03/test_webui_contract.py -q`
- 实现状态：`Implemented`（字符串契约测试函数已存在；**行为级**验证为 Gap G-UT-3）；执行状态与 Verdict 归 Run 报告（当前无录制 Run，见方案 §4 G-UT-1）。
