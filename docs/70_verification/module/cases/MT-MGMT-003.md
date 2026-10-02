<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-MGMT-003 — 分页快照冻结与用量清空计数

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-MGMT-003` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-MGMT-003.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-MGMT-003`）；责任摘要、分类与优先级以 [模块测试方案 §3](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-MGMT-003.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-MGMT-003` / M004 management §9 · `Admin.page`/`reset_usage`（组装） v0.1.0-draft.3 / VRC-MGMT-004（management-design §14 / management.isd §9.1，management 0.1.0-draft.3） / VRC-MGMT-004 / boundary / P0（[方案清单 §3](../llmtier-module-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：边界值（上限/零/空/刚好满、长度、分页越界）+ 条件边界（主要手段：无边界替身，全真实（仅 ENV-1/ENV-2 真实实现））
- **覆盖的分支 / 组合 / 迁移 ID**：无（层① 接口行为分母行）
- 要测什么（责任展开）：组装后分页与清空：首屏后更正旧页冻结、cursor 过期/跨 principal→400/403、范围清空计数一致（本 Case 责任：首屏快照对新写入冻结；cursor 错误码精确；范围清空计数与页面一致）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝management 组装后分页冻结与清空计数与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`management/admin.py::AdminService.page`/`mutate`、`inference/usage.py::UsageRecorder.page`/`reset_usage`

```text
page(data, actor, kind, cursor, limit); reset_usage(model, deployment_id, conn) -> {"deleted"}
```

- 初态构造（经公开入口）：`AppFixture` + `seed()`（ENV-1）+ ENV-2；用量经公开入口（服务方法）造数
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-2
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：`GET /v1/providers?limit=2` 后再新建 provider 并用 `next_cursor` 取第二页；`cursor=not-a-cursor`；`cursor=admin_missing:0`；`DELETE /v1/usage`（范围清空）
- 边界/非法取值及理由：首屏 2 条且 `has_more`；第二页不含新建资源、也不与首屏重叠；重复取同 cursor 结果稳定；垃圾/未知 cursor→400 `cursor_expired`；清空计数＝版本行数（2×head）且页面归零
- 规模 / 时间域（数量、分页、复杂度、观测开销）：6 请求 + 2 条用量；O(n log n) 排序

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `limit=2` 首屏 | 2 条 + `has_more=true` + 非空 `next_cursor` |
| 2 | 新建 provider 后取第二页 | 不含新资源、与首屏 id 不相交 |
| 3 | 再取同 cursor | 与步骤 2 完全一致（快照冻结） |
| 4 | 垃圾/未知 cursor | 均 400 `cursor_expired` |
| 5 | `DELETE /v1/usage` | `deleted=4`（2 请求 × 2 版本行）；再查页面 0 条 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：management 模块设计 §14.4 + 用量计数契约；按 `query_snapshots` 冻结语义与 `reset_usage` 的行数口径人工推导
- 互斥预期（成功 / 各错误分支）：快照冻结可复现；cursor 错误码精确；清空计数与页面一致

## 6. 错误路径、副作用与清理

- 错误出口与表现：400 `cursor_expired`（两形态）
- 副作用断言与清理：清空同时清 heads/versions/obligations/bindings

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-MGMT-003.py`（4 个）：`test_first_page_frozen_against_later_writes`、`test_garbage_cursor_is_400`、`test_unknown_snapshot_cursor_is_400`、`test_scoped_reset_count_matches`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-MGMT-003.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
