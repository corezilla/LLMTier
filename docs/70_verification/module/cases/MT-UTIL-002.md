<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-UTIL-002 — Store 组装后事务与迁移

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-UTIL-002` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-UTIL-002.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-UTIL-002`）；责任摘要、分类与优先级以 [模块测试方案 §3](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-UTIL-002.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-UTIL-002` / M007 util §9 · `transaction`/`migrate`（组装） v0.1.0-draft.2 / VRC-UTIL-002（util-design §14 / util.isd §9.1，util 0.1.0-draft.2） / VRC-UTIL-002 / recovery / P0（[方案清单 §3](../llmtier-module-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：故障注入 + 异常路径回滚 + 状态迁移断言（主要手段：无边界替身，全真实（仅 ENV-1/ENV-2 真实实现））
- **覆盖的分支 / 组合 / 迁移 ID**：迁移：T12
- 要测什么（责任展开）：组装后事务与迁移：回滚无半写、幂等 `migrate`、损坏库/版本不匹配拒绝、嵌套事务 409、并发启动（本 Case 责任：回滚无半写、migrate 幂等、版本不匹配拒绝、并发启动安全）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝util 组装后事务原子性与迁移幂等与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/util/store.py::Store.transaction`/`migrate`

```text
with store.transaction(True) as conn: ...; store.migrate()
```

- 初态构造（经公开入口）：临时目录 + 真实 `Store` 迁移（ENV-1）
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 组装隔离库
- 依赖的测试资产（tests.asset-design 文档）：无（全部真实实现；不经替身）

## 3. 输入构造

- 逐参数输入构造：事务内插入 1 行 `audit_events` 后抛 `RuntimeError`；`migrate()` 连调 3 次；4 线程并发 `Store+migrate`
- 边界/非法取值及理由：迁移后 `schema_version` 恒为 2；并发启动 4 线程全部成功；回滚后 `audit_events` 为空
- 规模 / 时间域（数量、分页、复杂度、观测开销）：单连接、4 线程并发迁移；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 事务内插入后抛 `RuntimeError` | `audit_events` 0 行（回滚无半写） |
| 2 | 连调 `migrate()` ×3 | 表集合不变、`schema_version` 恒等（幂等） |
| 3 | 经 `sqlite3` 原生连接改 `schema_meta.schema_version=99` 后 `migrate()` | 抛 503 `schema_version_mismatch` |
| 4 | 4 线程并发 `Store+migrate` | 无异常；`schema_meta` 仍单行（并发启动安全） |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：util 模块设计 §9 事务与迁移契约；按 SQLite 事务原子性与 `EXPECTED_SCHEMA_VERSION=2` 人工推导
- 互斥预期（成功 / 各错误分支）：回滚后无半写；`migrate` 幂等；版本不符 503 `schema_version_mismatch`；并发启动无冲突

## 6. 错误路径、副作用与清理

- 错误出口与表现：版本不匹配→503 `schema_version_mismatch`（不修复、不降级）
- 副作用断言与清理：失败迁移不写半行；并发启动后库可继续使用

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-UTIL-002.py`（4 个）：`test_rollback_leaves_no_half_write`、`test_migrate_idempotent`、`test_schema_version_mismatch_rejected`、`test_concurrent_startup_both_migrate`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-UTIL-002.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
