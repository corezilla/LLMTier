<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-MGMT-005 — AccountUsage 组装后账号用量视图

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-MGMT-005` |
| Document Version | `0.1.0-draft.2` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-10-02` |
| Last Modified Date | `2026-10-03` |
| Template ID | `tests.module-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/module/cases/MT-MGMT-005.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-MGMT-005`）；责任摘要、分类与优先级以 [模块测试方案 §6](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-MGMT-005.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-MGMT-005` / M004 management §9 · `AccountUsage.refresh`（组装） v0.1.0-draft.3 / VRC-MGMT-006（management-design §14 / management.isd §9.1，management 0.1.0-draft.3） / VRC-MGMT-006 / negative / P1（[方案清单 §6](../llmtier-module-test-scheme.md)）。
- **测试方法（§2.4 方法表行）**：错误猜测 + 反例驱动（非法字段/凭据/引用/类型/顺序）+ 判定表组合（主要手段：边界外协作者用 loopback `FakeUpstream`（探测 `/models` 与 account-usage 查询的真实 HTTP 面，资产 `llmtier-unit-fakes`））
- **覆盖的分支 / 组合 / 迁移 ID**：无（层① 接口行为分母行）；另覆盖方案 §7 缺口 `G-MT-COVERAGE-1` 的 `atomic=False` 审计例外（`admin.py::mutate(atomic=False)`，account usage refresh 走 `atomic=False` 路径，业务外部调用不占业务事务）。
- 要测什么（责任展开）：组装后账号用量：GET 不触网、未确认 POST、凭据缺失、provider 报错→`unavailable`+`error` 快照持久（本 Case 责任：`GET` 零触网返回 `not_refreshed`；未确认 400；凭据缺失/上游报错→`unavailable` 且快照持久）；另验证 `atomic=False`（account usage refresh）的审计例外语义——刷新成功落审计 `success` 行，失败落审计 `failed` 行，且不与业务同事务（失败时业务无半写）。
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝management 组装后账号用量四态视图与持久化与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`management/account_usage.py::AccountUsageService.latest`/`refresh`

```text
latest(provider_id) -> snapshot; refresh(provider_id, confirm_external_call) -> snapshot
```

- 初态构造（经公开入口）：`AppFixture` + `seed()`（ENV-1）+ ENV-2；provider 用量配置经公开 `POST /v1/providers`（`usage` 字段）；minimax URL 重指到 loopback 假上游（边界替身，不触真实外网）
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-2 + ENV-3（loopback 假上游承接 minimax 查询）
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：usage_provider：`none`（未刷新）、`local`（刷新→unlimited）、`minimax` 无凭据、`minimax` 有凭据（上游报错）；`confirm` 真/假/空体
- 边界/非法取值及理由：`GET` 不触网（上游命中 0）+ `not_refreshed`；空体→400 `invalid_request`（body 形状先检）；`confirm=false`→400 `confirmation_required`；无凭据→`credentials_missing`；上游报错→`provider_api_error` 且再 `GET` 仍返回错误快照
- 规模 / 时间域（数量、分页、复杂度、观测开销）：6 请求；上游命中计数断言；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `GET .../usage`（none） | 200 `not_refreshed`；上游命中数不变 |
| 2 | `POST` 不带确认字段 | 400 `invalid_request`（body 形状校验） |
| 3 | `POST` 显式 `confirm_external_call=false` | 400 `confirmation_required` |
| 4 | minimax 无凭据刷新 | `unavailable` + `credentials_missing` |
| 5 | minimax 有凭据刷新（上游报错） | `unavailable` + `provider_api_error` + `error` 非空；上游 +1 命中；再 `GET` 仍为该错误快照 |
| 6 | local 刷新 | `unlimited` |
| 7 | local 刷新后查审计（`atomic=False` 成功） | `/v1/audit` 含该 provider 的 `provider.usage.refresh` `result=success` 行 |
| 8 | 未知 provider 刷新（`atomic=False` 失败） | 404 `not_found`；`/v1/audit` 含 `target=provider_missing` 的 `result=failed` 行（`request_id` 非空）；业务无半写（`provider_usage_snapshots` 无该 provider 行） |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：management 模块设计 §14.6 + 账号用量契约；按 `latest`/`refresh` 的分支与快照持久化人工推导
- 互斥预期（成功 / 各错误分支）：四态视图互斥；`GET` 零触网；错误快照持久可复查；`atomic=False` 审计例外与业务事务分离——成功→审计 `success` 行；失败→审计 `failed` 行（`request_id` 非空）且业务无半写（`provider_usage_snapshots` 零写入）

## 6. 错误路径、副作用与清理

- 错误出口与表现：400 `invalid_request` / 400 `confirmation_required`
- 副作用断言与清理：快照写入 `provider_usage_snapshots`（幂等 upsert）

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-MGMT-005.py`（7 个）：`test_get_does_not_touch_network`、`test_refresh_without_confirm_is_400`、`test_minimax_missing_credentials_is_unavailable`、`test_provider_error_is_unavailable_and_persisted`、`test_local_provider_is_unlimited`、`test_non_atomic_refresh_success_is_audited`、`test_non_atomic_refresh_failure_is_audited_and_writes_nothing`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-MGMT-005.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
