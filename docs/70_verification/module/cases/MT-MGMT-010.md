<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-MGMT-010 — AccountUsage.refresh 四态分支

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-MGMT-010` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-MGMT-010.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-MGMT-010`）；责任摘要、分类与优先级以 [模块测试方案 §3](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-MGMT-010.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-MGMT-010` / M004 account refresh 四态：no-network/confirm/credentials/provider-error（组装） v0.1.0-draft.3 / VRC-MGMT-006（management-design §14 / management.isd §9.1，management 0.1.0-draft.3） / VRC-MGMT-006 / negative / P1（[方案清单 §3](../llmtier-module-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（非法字段/凭据/引用/类型/顺序）+ 判定表组合（主要手段：无边界替身，全真实（仅 ENV-1/ENV-2 真实实现））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M004-refresh 四态；组合：K7、K7
- 要测什么（责任展开）：GET 不触网；未确认→400；凭据缺失→`unavailable`；provider 报错→`unavailable`+`error` 持久（本 Case 责任：K7 组合行覆盖：确认门 400；local→unlimited；minimax/volc 无凭据→`credentials_missing`；none→unsupported；未知 provider→404）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝management 组装后账号用量刷新的四态出口与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`management/account_usage.py::refresh`（确认门 / provider 分派 / 凭据缺失）

```text
refresh(provider_id, confirm_external_call) -> snapshot
```

- 初态构造（经公开入口）：`AppFixture` + `seed()`（ENV-1）+ ENV-2；用量配置经公开 `POST /v1/providers`
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-2
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：`usage_provider`：local/minimax/volc/none；`confirm_external_call` 真/假；未知 provider
- 边界/非法取值及理由：确认门→400 `confirmation_required`；local→`unlimited`；minimax 无凭据→`unavailable`+`credentials_missing`；volc 无凭据→`unavailable`+`volc_get_coding_plan_usage_requires_ak_sk`；none→`unsupported`+`provider_usage_unsupported`；未知 provider→404
- 规模 / 时间域（数量、分页、复杂度、观测开销）：6 请求；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | local 已确认 | `unlimited` |
| 2 | minimax 有凭据但未确认 | 400 `confirmation_required` |
| 3 | minimax 无凭据已确认 | `unavailable` + `credentials_missing` |
| 4 | volc 无凭据已确认 | `unavailable` + `volc_get_coding_plan_usage_requires_ak_sk` |
| 5 | none 已确认 | `unsupported` + `provider_usage_unsupported` |
| 6 | 未知 provider | 404 `not_found` |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：方案 §3.3 K7 + management 模块设计 §14.6；按 `refresh` 的 `require` 门与 provider 分派人工推导
- 互斥预期（成功 / 各错误分支）：K7 组合行覆盖；四种 status 互斥且 `error` 串稳定

## 6. 错误路径、副作用与清理

- 错误出口与表现：400 `confirmation_required` / 404 `not_found`
- 副作用断言与清理：每次刷新 upsert 快照（不产生外部计费）

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-MGMT-010.py`（6 个）：`test_local_no_credentials_confirmed_is_unlimited`、`test_minimax_with_credentials_unconfirmed_is_400`、`test_minimax_without_credentials_confirmed_is_unavailable`、`test_volc_without_credentials_confirmed_is_unavailable`、`test_none_provider_is_unsupported`、`test_unknown_provider_is_404`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-MGMT-010.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
