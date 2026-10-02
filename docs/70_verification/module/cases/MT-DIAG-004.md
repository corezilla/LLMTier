<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-DIAG-004 — set_injections 分支与启用/撤销迁移

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-DIAG-004` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-DIAG-004.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-DIAG-004`）；责任摘要、分类与优先级以 [模块测试方案 §3](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-DIAG-004.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-DIAG-004` / M006 `set_injections` 分支：非 list 400/未知 deployment 404/空 items revoke（组装） v0.1.0-draft.6 / VRC-DIAG-004（libdiag-design §14 / libdiag.isd §9.1，libdiag 0.1.0-draft.6） / VRC-DIAG-004 / negative / P0（[方案清单 §3](../llmtier-module-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（非法字段/凭据/引用/类型/顺序）+ 判定表组合（主要手段：无边界替身，全真实（仅 ENV-1/ENV-2 真实实现））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M006-set_injections 三分支；迁移：T10、T11、T10/T11
- 要测什么（责任展开）：非 list→400；未知 deployment→404；`items:[]` 撤销全部注入（DELETE）（本 Case 责任：非 list 400/未知 deployment 404/`items:[]` 撤销三分支互斥；T10/T11 迁移完整；作用域隔离）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝libdiag 组装后注入写入三分支与状态迁移与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`libdiag/injections.py::set_injections`（非 list/未知 deployment/空 items 撤销/UPSERT）

```text
set_injections(deployment_id, actor_items, conn=None) -> list; injections(deployment_id)
```

- 初态构造（经公开入口）：`AppFixture` 真实组装（ENV-1）
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-4
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture` + `tests/module/cases/support/inference_env.py::InferenceEnv`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：`actor_items` 为 `"x"/5/{...}`；未知 deployment（含 `injections()` 读取）；`items:[]`（先配 2 类）；同类型二次配置（UPSERT）；跨 deployment 隔离
- 边界/非法取值及理由：非 list→400 `invalid_injection`；未知 deployment→404 `not_found`（读写两向）；`items:[]` 撤销全部且 `enabled_injection` 变 None（T11）；无注入时 `enabled_injection` 为 None（T10 起点）；同类型 UPSERT 替换配置值；注入按 deployment 隔离
- 规模 / 时间域（数量、分页、复杂度、观测开销）：6 个测试方法；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 非 list 三形态 | 均 400 `invalid_injection` |
| 2 | 未知 deployment 写与读 | 均 404 `not_found` |
| 3 | T10：无→启用 `rate_limit` | `enabled_injection()` 返回 `rate_limit`（`retry_after_sec=3`） |
| 4 | T11：配 2 类后 `items:[]` | 读回 0 条；前置与流阶段 `enabled_*` 均为 None |
| 5 | 同类型 UPSERT（1→9） | 读回 1 条且 `retry_after_sec=9` |
| 6 | Senior 配注入后查 Embedding-v1 | 读回 0 条且 `enabled_injection()` 为 None |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：libdiag 模块设计 §14.4 + 方案 §3.4 T10/T11；按 `set_injections` 的两个前置校验与 `txn` 撤销分支人工推导
- 互斥预期（成功 / 各错误分支）：三分支互斥；启用/撤销迁移完整；作用域隔离

## 6. 错误路径、副作用与清理

- 错误出口与表现：400 `invalid_injection` / 404 `not_found`
- 副作用断言与清理：撤销为 DELETE 全部行（按 deployment 限定）

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-DIAG-004.py`（6 个）：`test_non_list_is_400`、`test_unknown_deployment_is_404`、`test_t10_enable_then_hit`、`test_t11_revoke_by_empty_items`、`test_upsert_replaces_same_type`、`test_injections_are_scoped_to_deployment`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-DIAG-004.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
