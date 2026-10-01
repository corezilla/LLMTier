<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-UI-010 — statsRange/etag/fetchProviderModels 契约分支

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-UI-010` |
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
| Canonical Path | `docs/70_verification/specifications/unit-case-UT-UI-010.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-UI-010`）；责任摘要、分类与优先级以 [单元测试方案 §3](../schemes/llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [web-ui](../../40_module_design/web-ui-design.md) §14 / ISD [web-ui.isd.md](../../50_implementation_design/web-ui.isd.md) §9.1，设计验证项 `VRC-UI-001`（固定版本 `web-ui 0.1.0-draft.2`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `web_ui`；裁剪依据见 [STD 裁剪清单](../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-UI-010` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-UI-010` / M002 web-ui §14.1/§14.5 · `statsRange`/`etag`/`fetchProviderModels` v0.1.0-draft.2 / `VRC-UI-001` / boundary / P2（[方案清单 §3](../schemes/llmtier-unit-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：边界值（时间窗/etag 格式/cache 边界）
- 要测什么（责任展开）：被测（字符串契约层）：`statsRange` 24h/7d/today/all；`etag()` 格式 `"<id>.v<n>"`；`fetchProviderModels` cache 命中/未命中与失败吞没（`catch{return []}`）。
- 明确不测什么 / 失败含义：不测：`app.js` 运行时行为（G-UT-3）；不测统计口径（UT-OBS-002/UT-DIAG-002）。失败含义＝统计范围/ETag/模型缓存分支源码契约缺失。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/web_ui/app.js` 的 `statsRange`/`etag`/`fetchProviderModels` 源片段

```text
function statsRange(); const etag=item=>`"${item.id}.v${item.version}"`; fetchProviderModels(providerId)
```

- 初态构造（经公开入口）：读取真实 `src/web_ui/app.js` 文件文本
- Fixture / 向量及版本：`tests/unit/v03/test_webui_contract.py::WebUIBranchContractTests`
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../plans/llmtier-unit-test-plan.md) 分配）：无（静态文件读取，真实产物）
- 依赖的测试资产（tests.asset-design 文档）：无（真实静态产物）

## 3. 输入构造

- 逐参数输入构造：`app.js` 源文本
- 边界/非法取值及理由：断言 `statsRange` 定义、`etag` 格式串、cache 命中短路、失败吞没
- 规模 / 时间域（数量、分页、复杂度、观测开销）：单文件文本，O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 断言 `statsRange` 定义 | `function statsRange()` |
| 2 | 断言 ETag 格式串 | `const etag=item=>`\`"${item.id}.v${item.version}"\`` |
| 3 | 断言 cache 命中短路 | `if(state.modelCache[providerId]) return state.modelCache[providerId]` |
| 4 | 断言失败吞没 | `catch{return []}` |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：web-ui §14.1/§14.5 契约（`<id>.v<n>`、cache） + 人工比对源码；字符串契约层。**判据语义以设计验证项 `VRC-UI-001` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：`statsRange`/`etag`/cache/失败吞没 token 存在且格式正确；互斥

## 6. 错误路径、副作用与清理

- 错误出口与表现：无运行时错误出口（静态断言）
- 副作用断言与清理：无（只读源代码）

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/v03/test_webui_contract.py::WebUIBranchContractTests::test_stats_range_and_etag_and_model_cache`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/v03/test_webui_contract.py -q`
- 实现状态：`Implemented`（字符串契约测试函数已存在；**行为级**验证为 Gap G-UT-3）；执行状态与 Verdict 归 Run 报告（当前无录制 Run，见方案 §4 G-UT-1）。
