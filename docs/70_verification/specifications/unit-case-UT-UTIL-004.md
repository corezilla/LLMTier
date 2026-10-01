<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-UTIL-004 — 损坏库、迁移回滚与嵌套事务并发启动

> STD 使用入口：[项目采用说明与标准导航](../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-UTIL-004` |
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
| Canonical Path | `docs/70_verification/specifications/unit-case-UT-UTIL-004.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-UTIL-004`）；责任摘要、分类与优先级以 [单元测试方案 §3](../schemes/llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [util](../../40_module_design/util-design.md) §14 / ISD [util.isd.md](../../50_implementation_design/util.isd.md) §9.1，设计验证项 `VRC-UTIL-002`（固定版本 `util 0.1.0-draft.1`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `util`；裁剪依据见 [STD 裁剪清单](../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-UTIL-004` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-UTIL-004` / M007 util §14.2 · `migrate`/`_initialize` v0.1.0-draft.1 / `VRC-UTIL-002` / concurrency / P1（[方案清单 §3](../schemes/llmtier-unit-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：线程对偶 + 受控时序（并发启动/嵌套事务/损坏库映射）
- 要测什么（责任展开）：被测：损坏文件→`schema_integrity_failed`；迁移中途失败→回滚空库；嵌套事务→`E-UTIL-NESTED-TXN`（409）；并发启动两实例。
- 明确不测什么 / 失败含义：不测：幂等 migrate 主路径（UT-UTIL-002）；不测 symlink（UT-UTIL-001）。失败含义＝完整性/迁移原子性/嵌套事务/并发初始化实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/util/store.py::Store.migrate`/`_initialize`/`transaction`（integrity_check、版本、嵌套检测）

```text
Store.migrate(); Store.transaction(immediate=True); Store(path)
```

- 初态构造（经公开入口）：`tempfile.TemporaryDirectory` 隔离库；损坏文件、迁移中途失败、嵌套事务、两实例并发（ENV-1）
- Fixture / 向量及版本：`tests/unit/v03/test_store_gaps.py::IntegrityMappingTests`/`NestedTransactionTests`/`CorruptStoreTests`；`test_store_schema.py`
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../plans/llmtier-unit-test-plan.md) 分配）：ENV-1 隔离 Python 临时库
- 依赖的测试资产（tests.asset-design 文档）：无（真实 SQLite）

## 3. 输入构造

- 逐参数输入构造：损坏库文件；migrate 中途异常；嵌套 `txn(conn)`；两 Store 并发 migrate
- 边界/非法取值及理由：损坏→`schema_integrity_failed`；中途失败→空库；嵌套→409；并发一胜一全
- 规模 / 时间域（数量、分页、复杂度、观测开销）：O(迁移语句)；并发 2 实例

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 损坏库 | `schema_integrity_failed`（503） |
| 2 | 迁移中途失败 | 回滚空库、无半表 |
| 3 | 嵌套事务 | `E-UTIL-NESTED-TXN`（409） |
| 4 | 并发两实例 | 一个成功、一个收敛（无损坏） |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：`T-UTIL-05/10`/`RULE-UTIL-MIGRATE` + 人工推导；不调用被测复算。**判据语义以设计验证项 `VRC-UTIL-002` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：损坏`schema_integrity_failed`；中途失败回滚空库；嵌套 409；并发启动收敛；互斥

## 6. 错误路径、副作用与清理

- 错误出口与表现：`schema_integrity_failed`（503）；嵌套 409；无第三态。**注意**：`CorruptStoreTests` 记录具名缺口 G-UT-5——损坏文件当前抛原始异常而非 `schema_integrity_failed`（见该测试 docstring）
- 副作用断言与清理：失败迁移无半写；临时库由 fixture 清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/v03/test_store_gaps.py::IntegrityMappingTests::test_integrity_failure_is_503` / `NestedTransactionTests::test_nested_transaction_is_409` / `test_txn_context_reuses_caller_connection` / `CorruptStoreTests::test_corrupt_file_raises`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/v03/test_store_gaps.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit/v03/test_store_gaps.py`）；`CorruptStoreTests` 另绑定缺口 G-UT-5；执行状态与 Verdict 归 Run 报告（当前无录制 Run，见方案 §4 G-UT-1）。
