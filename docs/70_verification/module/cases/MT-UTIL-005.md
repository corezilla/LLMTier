<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-UTIL-005 — 嵌套事务 409 与迁移中途失败回滚

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-UTIL-005` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-UTIL-005.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-UTIL-005`）；责任摘要、分类与优先级以 [模块测试方案 §3](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-UTIL-005.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-UTIL-005` / M007 事务分支：嵌套 409 + 迁移中途失败回滚（组装） v0.1.0-draft.2 / VRC-UTIL-002（util-design §14 / util.isd §9.1，util 0.1.0-draft.2） / VRC-UTIL-002 / recovery / P1（[方案清单 §3](../llmtier-module-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：故障注入 + 异常路径回滚 + 状态迁移断言（主要手段：无边界替身，全真实（仅 ENV-1/ENV-2 真实实现））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M007-嵌套 409/迁移回滚；迁移：T13、T12/T13
- 要测什么（责任展开）：嵌套事务→409 `E-UTIL-NESTED-TXN`；迁移中途失败回滚为可启动空库（本 Case 责任：同连接重复 BEGIN→409；页配额耗尽致迁移中途失败→整体回滚为可启动空库）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝util 组装后嵌套事务与迁移回滚与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/util/store.py::Store.transaction`/`_initialize`、`util/store.py::txn`

```text
with store.transaction(True) as conn: ...  # 嵌套再次 BEGIN -> 409
```

- 初态构造（经公开入口）：临时目录 + 真实 `Store`（迁移中途失败经 SQLite 页配额注入）
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 组装隔离库
- 依赖的测试资产（tests.asset-design 文档）：无（全部真实实现；不经替身）

## 3. 输入构造

- 逐参数输入构造：① 同一连接内嵌套 `transaction(True)`；② `txn(store, conn)` 复用调用方连接；③ `PRAGMA max_page_count=3` 后 `migrate()`
- 边界/非法取值及理由：嵌套 `BEGIN`→409 `E-UTIL-NESTED-TXN`；页配额耗尽→迁移整体回滚、零残留表；换新连接可完整迁移
- 规模 / 时间域（数量、分页、复杂度、观测开销）：单连接；迁移 SQL 逐条执行至配额上限；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 事务内再次 `transaction(True)` | 409 `E-UTIL-NESTED-TXN` |
| 2 | `txn(store, conn)` 内层 | 内层即调用方连接（不开第二个事务） |
| 3 | `max_page_count=3` 后 `migrate()` | 抛 `sqlite3.OperationalError`（disk full） |
| 4 | 失败后读 `sqlite_master` | 表集合为空（回滚无半写） |
| 5 | 新连接 `migrate()` | 23 张表 + `schema_version=2`（可重启） |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：util 模块设计 §9 + ISD 嵌套事务策略；按 `BEGIN IMMEDIATE` 的 SQLite 语义与 `_initialize` 单事务回滚人工推导
- 互斥预期（成功 / 各错误分支）：嵌套 409；配额失败→零残留；新连接可完整迁移（回滚为可启动空库）

## 6. 错误路径、副作用与清理

- 错误出口与表现：嵌套事务 409；页配额耗尽抛 `OperationalError`（存储面异常，非 ApiError）
- 副作用断言与清理：回滚后无半写；失败库可重新初始化

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-UTIL-005.py`（3 个）：`test_nested_begin_is_409_nested_txn`、`test_txn_helper_yields_caller_connection_without_nested_begin`、`test_mid_migration_failure_rolls_back_to_reusable_empty`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-UTIL-005.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
