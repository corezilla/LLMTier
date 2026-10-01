<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-UTIL-002 — 事务、迁移与损坏库拒绝

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-UTIL-002` |
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
| Canonical Path | `docs/70_verification/unit/cases/UT-UTIL-002.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-UTIL-002`）；责任摘要、分类与优先级以 [单元测试方案 §3](../llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [util-design.md](../../../40_module_design/util-design.md) §14 / ISD [util.isd.md](../../../50_implementation_design/util.isd.md) §9.1，设计验证项 `VRC-UTIL-002`（固定版本 `util 0.1.0-draft.1`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `UTIL`；裁剪依据见 [STD 裁剪清单](../../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-UTIL-002` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-UTIL-002` / `VRC-UTIL-002`（util 模块设计 §14 / util-isd §9.1，util 0.1.0-draft.1） / `VRC-UTIL-002` / recovery / P0（[方案清单 §3](../llmtier-unit-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：故障注入 + 异常路径恢复（回滚/幂等 migrate/损坏库/版本不匹配）
- 要测什么（责任展开）：被测：事务中途异常回滚、`migrate()` 幂等、损坏库/版本不匹配拒绝、无 `schema_meta` 旧库拒绝、持久化跨重开。
- 明确不测什么 / 失败含义：不测：真实多进程并发启动压测（系统层可补充）；不测业务表语义。失败含义＝回滚/迁移/拒绝实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/util/store.py::Store.transaction/migrate`；`EXPECTED_SCHEMA_VERSION`

```text
Store.transaction(); Store.migrate(); schema_meta
```

- 初态构造（经公开入口）：`tempfile.TemporaryDirectory` 隔离库（ENV-1）
- Fixture / 向量及版本：`tests/unit/cases/UT-UTIL-002.py`/`test_store_schema.py`
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../llmtier-unit-test-plan.md) 分配）：ENV-1 隔离 Python 临时库 / ENV-2 loopback 测试 HTTP 实例 / ENV-3 provider 进程内 fake（按 Case 需要，见 §4）
- 依赖的测试资产（tests.asset-design 文档）：无（真实 SQLite）

## 3. 输入构造

- 逐参数输入构造：事务内抛异常；连续 migrate；版本=99；有表无 schema_meta；重开库
- 边界/非法取值及理由：版本匹配边界；空表 vs 有表
- 规模 / 时间域（数量、分页、复杂度、观测开销）：O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 事务回滚 | 无半写 |
| 2 | migrate 幂等 | schema_meta 1 行 |
| 3 | 版本不匹配 | 503 schema_version_mismatch |
| 4 | 无版本表旧库 | schema_unknown |
| 5 | 持久化跨重开 | 表存在 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：`RULE-UTIL-TXN/MIGRATE`；人工推导。**判据语义以设计验证项 `VRC-UTIL-002` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：回滚后值恢复 NULL；幂等；版本 99→`schema_version_mismatch`；无表→`schema_unknown`；重开表在

## 6. 错误路径、副作用与清理

- 错误出口与表现：无（分支互斥）
- 副作用断言与清理：隔离库回滚；无清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/cases/UT-UTIL-002.py::test_transaction_rolls_back/test_migration_is_idempotent` + `test_store_schema.py::test_fresh_init_sets_expected_version_and_rerun_is_safe/test_persistence_across_reopen/test_version_mismatch_rejected/test_legacy_store_without_schema_meta_rejected`（注意：本 Case 的测试函数当前按子句（test case method）映射；若与设计 VRC 不一致，以设计修订回溯后重裁）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/cases/store.py tests/unit/cases/store_schema.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit`）；执行状态与 Verdict 归 Run 报告（当前无录制 Run，见方案 §4 G-UT-1）。

