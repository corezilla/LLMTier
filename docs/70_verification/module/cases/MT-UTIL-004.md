<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-UTIL-004 — migrate 四拒绝出口与幂等

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-UTIL-004` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-UTIL-004.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-UTIL-004`）；责任摘要、分类与优先级以 [模块测试方案 §3](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-UTIL-004.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-UTIL-004` / M007 migrate 四拒绝出口：schema_unknown/版本不匹配/完整性失败 + 幂等（组装） v0.1.0-draft.2 / VRC-UTIL-002（util-design §14 / util.isd §9.1，util 0.1.0-draft.2） / VRC-UTIL-002 / recovery / P0（[方案清单 §3](../llmtier-module-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：故障注入 + 异常路径回滚 + 状态迁移断言（主要手段：无边界替身，全真实（仅 ENV-1/ENV-2 真实实现））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M007-migrate 四拒绝出口
- 要测什么（责任展开）：无 schema_meta 但有表→503 `schema_unknown`；版本不匹配→503；完整性失败→503 `schema_integrity_failed`；重复 `migrate` 幂等（本 Case 责任：schema_unknown／版本不匹配／完整性失败三拒绝出口与重复迁移幂等）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝util 组装后迁移拒绝出口与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/util/store.py::Store.migrate`

```text
store.migrate()  # schema_unknown / version / integrity / 幂等
```

- 初态构造（经公开入口）：临时目录 + 真实 SQLite 文件（坏状态经 `sqlite3`/字节注入，方案 §1.5 存储面）
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 组装隔离库
- 依赖的测试资产（tests.asset-design 文档）：无（全部真实实现；不经替身）

## 3. 输入构造

- 逐参数输入构造：① 无 `schema_meta` 但有 `legacy` 表；② `schema_meta.schema_version=3`；③ 完好库 + 损坏第 4 页（4 KiB `0xDEADBEEF` 覆写）；④ 完好库连调 `migrate`
- 边界/非法取值及理由：三个拒绝出口 `code` 精确匹配；`PRAGMA integrity_check` 非 `ok` 即拒；重复迁移表集合不变
- 规模 / 时间域（数量、分页、复杂度、观测开销）：200 行 `audit_events` 撑出多页；单连接；O(n)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 旧库（无 `schema_meta`）`migrate()` | 503 `schema_unknown` |
| 2 | 改 `schema_version=3` 后 `migrate()` | 503 `schema_version_mismatch` |
| 3 | 损坏中间页后 `migrate()` | 503 `schema_integrity_failed`（消息含 integrity_check 摘要） |
| 4 | 完好库连调 `migrate()` | 表集合不变、版本不变 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：util 模块设计 §9 + 方案 §1.5.1 a31/a32/a33；按 `migrate()` 分支顺序与 SQLite 行为人工推导
- 互斥预期（成功 / 各错误分支）：三码精确；重复迁移幂等

## 6. 错误路径、副作用与清理

- 错误出口与表现：`schema_unknown` / `schema_version_mismatch` / `schema_integrity_failed` 三个 503 互斥，不自动修复/降级
- 副作用断言与清理：失败迁移不写半行；库保持原状

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-UTIL-004.py`（4 个）：`test_tables_without_schema_meta_is_schema_unknown`、`test_version_mismatch_rejected`、`test_corrupted_page_is_integrity_failed`、`test_repeated_migrate_is_idempotent`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-UTIL-004.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
