<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-MGMT-002 — Registry CRUD 组装不变量与审计同事务

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-MGMT-002` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-MGMT-002.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-MGMT-002`）；责任摘要、分类与优先级以 [模块测试方案 §3](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-MGMT-002.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-MGMT-002` / M004 management §9 · `Registry` CRUD（组装） v0.1.0-draft.3 / VRC-MGMT-002（management-design §14 / management.isd §9.1，management 0.1.0-draft.3） / VRC-MGMT-002 / negative / P0（[方案清单 §3](../llmtier-module-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（非法字段/凭据/引用/类型/顺序）+ 判定表组合（主要手段：无边界替身，全真实（仅 ENV-1/ENV-2 真实实现））
- **覆盖的分支 / 组合 / 迁移 ID**：无（层① 接口行为分母行）
- 要测什么（责任展开）：组装后 CRUD 不变量：ETag stale 412、删除被引用、能力冲突、`Embedding-v1` 冻结、审计同事务（本 Case 责任：412/409 不变量成立；成功与失败变异均落审计且带 `request_id`；失败无业务半写）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝management 组装后CRUD 不变量与审计同事务与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`registry.py::update_*`/`delete_*`、`management/admin.py::AdminService.mutate`、`audit.py::AuditLog.record`

```text
update_provider(rid, body, if_match); delete_provider(rid, if_match); admin.mutate(actor, action, target, request_id, fn)
```

- 初态构造（经公开入口）：`AppFixture` + `seed()`（ENV-1）+ ENV-2；ETag 经公开 `GET`/`POST` 响应头
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-2
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：provider/deployment 创建→改→删；被引用删除；`Embedding-v1` 绑定非向量成员；`GET /v1/audit`
- 边界/非法取值及理由：陈旧 ETag→412 `version_conflict`（含 `current_version`）；被引用删除→409 `resource_in_use`；能力冲突→409；成功/失败均落审计（`result=success`/`failed`）且带 `request_id`
- 规模 / 时间域（数量、分页、复杂度、观测开销）：6 请求 + 审计查询；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 改一次后用旧 ETag 再改 | 412 `version_conflict`，`current_version=2` |
| 2 | 删除有 deployment 的 provider | 409 `resource_in_use` |
| 3 | 删除已被 tier 绑定的 deployment | 409 `resource_in_use` |
| 4 | `Embedding-v1` 绑定 responses 成员 | 409（`embedding_space_conflict`/`capability_conflict`） |
| 5 | `GET /v1/audit` | 存在 `provider.create`/`provider.update` 成功行与 `result=failed` 行（均带 `request_id`） |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：management 模块设计 §14.2/§14.3 + 错误码契约；按 `mutate` 的事务边界与审计写入路径人工推导
- 互斥预期（成功 / 各错误分支）：412/409 码精确；审计与业务同事务（失败亦留痕且业务无半写）

## 6. 错误路径、副作用与清理

- 错误出口与表现：412 `version_conflict` / 409 `resource_in_use` / 409 `capability_conflict`
- 副作用断言与清理：失败变异不落业务半成品；审计两侧均有行

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-MGMT-002.py`（5 个）：`test_stale_etag_is_412_with_current_version`、`test_delete_referenced_provider_is_409_in_use`、`test_delete_referenced_deployment_is_409_in_use`、`test_capability_conflict_on_tier_bind`、`test_audit_records_success_and_failed`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-MGMT-002.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
