<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-MGMT-008 — 引用删除 resource_in_use 409

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-MGMT-008` |
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
| Canonical Path | `docs/70_verification/unit/cases/UT-MGMT-008.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-MGMT-008`）；责任摘要、分类与优先级以 [单元测试方案 §3](../llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [management](../../../40_module_design/management-design.md) §14 / ISD [management.isd.md](../../../50_implementation_design/management.isd.md) §9.1，设计验证项 `VRC-MGMT-002`（固定版本 `management 0.1.0-draft.3`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `management`；裁剪依据见 [STD 裁剪清单](../../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-MGMT-008` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-MGMT-008` / M004 management §14.2 · `Registry` 引用删除 v0.1.0-draft.2 / `VRC-MGMT-002` / negative / P1（[方案清单 §3](../llmtier-unit-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（resource_in_use 409）
- 要测什么（责任展开）：被测：`resource_in_use`——删除被 deployment 引用的 provider、删除被 tier 引用的 deployment → 409。
- 明确不测什么 / 失败含义：不测：其它 CRUD 不变量（UT-MGMT-002）；不测并发 PATCH。失败含义＝引用完整性检查实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/management/registry.py` 的删除路径（`delete_provider`/`delete_deployment` 的引用检查）

```text
Registry.delete_provider(provider_id, conn=None); Registry.delete_deployment(deployment_id, conn=None)
```

- 初态构造（经公开入口）：`AppFixture().seed()` 建 provider→deployment→tier 引用链（ENV-1）
- Fixture / 向量及版本：`tests/unit/cases/UT-MGMT-008.py::ResourceInUseTests`；`fakes.py::AppFixture`（ENV-1）
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../llmtier-unit-test-plan.md) 分配）：ENV-1 隔离 Python 临时库
- 依赖的测试资产（tests.asset-design 文档）：无（真实实现）

## 3. 输入构造

- 逐参数输入构造：删除被 deployment 引用的 provider；删除被 tier 引用的 deployment
- 边界/非法取值及理由：被引用→409（二分支互斥）
- 规模 / 时间域（数量、分页、复杂度、观测开销）：单次删除，O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 删除被引用 provider | 409 `resource_in_use` |
| 2 | 删除被引用 deployment | 409 `resource_in_use` |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：`RULE-MGMT-REF` 引用规则 + 人工推导；不调用被测复算。**判据语义以设计验证项 `VRC-MGMT-002` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：两删除路径均 409 `resource_in_use`；互斥

## 6. 错误路径、副作用与清理

- 错误出口与表现：409 `resource_in_use`；无第三态
- 副作用断言与清理：被拒绝删除不改变库；隔离库由 fixture 清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/cases/UT-MGMT-008.py::ResourceInUseTests::test_delete_provider_referenced_by_deployment_is_409` / `test_delete_deployment_referenced_by_tier_is_409`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/cases/management_gaps.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit/cases/UT-MGMT-008.py`）；执行状态与 Verdict 归 Run 报告（当前无录制 Run，见方案 §4 G-UT-1）。
