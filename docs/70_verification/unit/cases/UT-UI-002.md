<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-UI-002 — 编辑并发与鉴权呈现

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-UI-002` |
| Document Version | `0.1.0-draft.3` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-30` |
| Last Modified Date | `2026-10-03` |
| Template ID | `tests.unit-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/unit/cases/UT-UI-002.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-UI-002`）；责任摘要、分类与优先级以 [单元测试方案 §6](../llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [web-ui-design.md](../../../40_module_design/web-ui-design.md) §14 / ISD [web-ui.isd.md](../../../50_implementation_design/web-ui.isd.md) §9.1，设计验证项 `VRC-UI-002`（固定版本 `web-ui 0.1.0-draft.2`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `UI`；裁剪依据见 [STD 裁剪清单](../../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-UI-002` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-UI-002` / `VRC-UI-002`（web-ui 模块设计 §14 / web-ui-isd §9.1，web-ui 0.1.0-draft.2） / `VRC-UI-002` / negative / P0（[方案清单 §6](../llmtier-unit-test-scheme.md)）。
- **测试方法（§2.1 方法表行）**：错误猜测 + 反例驱动（412/409/401-403/429 分支）（主要手段：直接调用 + 冻结向量）
- 要测什么（责任展开）：被测：UI 契约中 ETag/引用/鉴权错误的呈现路径（412 stale 复用既有 provider、401/403 处理、分区不猜）。
- 明确不测什么 / 失败含义：本 Case 只做源码字符串契约；**真实浏览器并发编辑/确认门控归系统层 `ST-UI-003/007`（`tests/system/cases/` (ST-UI-*)，已关闭 `RISK-UI-EXEC-1`）**；不测后端 ETag 生成（归 M004）。失败含义＝UI 错误处理/鉴权呈现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/web_ui/app.js`（`api`/`tierState`/错误分派文本契约）

```text
静态契约：`app.js` 文本
```

- 初态构造（经公开入口）：读取真实 `app.js`
- Fixture / 向量及版本：`tests/unit/cases/UT-UI-002.py::setUpClass`
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../llmtier-unit-test-plan.md) 分配）：ENV-1 隔离 Python 临时库 / ENV-2 loopback 测试 HTTP 实例 / ENV-3 provider 进程内 fake（按 Case 需要，见 §4）
- 依赖的测试资产（tests.asset-design 文档）：无（真实产物）

## 3. 输入构造

- 逐参数输入构造：`app.js` 文本（ETag/错误分派 token）
- 边界/非法取值及理由：412/409/401/403 分支呈现 token
- 规模 / 时间域（数量、分页、复杂度、观测开销）：单文件读取，O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 读取 `app.js` | 文本 |
| 2 | 断言复用既有 provider 的编辑路径 | `test_tier_member_editor_uses_existing_provider` |
| 3 | 断言后端暂停/恢复复用 deployment PATCH | `test_model_pause_resume_uses_existing_deployment_patch` |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：web-ui 设计 §9 错误呈现契约；人工枚举。**判据语义以设计验证项 `VRC-UI-002` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：编辑走既有 provider 端点；pause/resume 走既有 deployment PATCH；错误呈现分支存在

## 6. 错误路径、副作用与清理

- 错误出口与表现：无（静态契约）
- 副作用断言与清理：只读；无清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/cases/UT-UI-002.py::test_tier_member_editor_uses_existing_provider/test_model_pause_resume_uses_existing_deployment_patch/test_tier_parent_type_cell_is_empty`（注意：本 Case 的测试函数当前按子句（test case method）映射；若与设计 VRC 不一致，以设计修订回溯后重裁）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/cases/UT-UI-002.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit`）；执行状态与 Verdict 见 Run 报告 `run-20261001-04`。

