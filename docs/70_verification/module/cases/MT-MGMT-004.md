<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-MGMT-004 — Admin.probe 组装后探测

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-MGMT-004` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-MGMT-004.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-MGMT-004`）；责任摘要、分类与优先级以 [模块测试方案 §6](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-MGMT-004.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-MGMT-004` / M004 management §9 · `Admin.probe`（组装） v0.1.0-draft.3 / VRC-MGMT-005（management-design §14 / management.isd §9.1，management 0.1.0-draft.3） / VRC-MGMT-005 / normal / P1（[方案清单 §6](../llmtier-module-test-scheme.md)）。
- **测试方法（§2.4 方法表行）**：组装后真实调用 + 等价类划分 + 分支覆盖（主要手段：边界外协作者用 loopback `FakeUpstream`（探测 `/models` 与 account-usage 查询的真实 HTTP 面，资产 `llmtier-unit-fakes`））
- **覆盖的分支 / 组合 / 迁移 ID**：无（层① 接口行为分母行）
- 要测什么（责任展开）：组装后探测：未确认 400、正常探测、不可达落 `unhealthy`、`may_have_incurred_cost`（本 Case 责任：确认门→400；可达→healthy 落库、不可达→unhealthy 落库；成本标志为 false）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝management 组装后探测的确认门与落库语义与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`management/admin.py::AdminService.probe`、`http_api/health.py::apply_probe_result`

```text
probe(actor, body, request_id) -> {deployment_id, status, checked_at, may_have_incurred_cost}
```

- 初态构造（经公开入口）：`AppFixture` + `seed()`（ENV-1）+ ENV-2；provider endpoint 指向 loopback `FakeUpstream` 或不可达端口
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-2 + ENV-3（loopback 假上游 `/models`）
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：body 缺 `confirm_external_call`；带多余字段；`endpoint=假上游`；`endpoint=http://127.0.0.1:9`；未知 deployment
- 边界/非法取值及理由：未确认/多余字段→400 `confirmation_required`；可达→`healthy` 且 `deployments.health` 落库；不可达→`unhealthy` 落库；`may_have_incurred_cost=false`；未知 deployment→404
- 规模 / 时间域（数量、分页、复杂度、观测开销）：5 次探测 + 2 次资源查询；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 不带确认字段 | 400 `confirmation_required` |
| 2 | 带多余字段 | 400 `confirmation_required` |
| 3 | 探测假上游 | 200 `healthy`，`may_have_incurred_cost=false`；`GET /v1/deployments/{id}` 的 `health=healthy` |
| 4 | 探测不可达端口 | 200 `unhealthy`；资源 `health=unhealthy` |
| 5 | 探测未知 deployment | 404 |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：management 模块设计 §14.5 + 探测契约；按 `probe` 的确认校验与 `apply_probe_result` 事务人工推导
- 互斥预期（成功 / 各错误分支）：确认门、落库健康态、成本标志三面一致；未知资源 404

## 6. 错误路径、副作用与清理

- 错误出口与表现：400 `confirmation_required` / 404 `not_found`
- 副作用断言与清理：探测结果写 `deployments.health` 与 `probe_results`

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-MGMT-004.py`（5 个）：`test_unconfirmed_probe_is_400_confirmation_required`、`test_probe_extra_field_is_400`、`test_reachable_upstream_probe_is_healthy_persisted`、`test_unreachable_probe_is_unhealthy_persisted`、`test_probe_unknown_deployment_is_404`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-MGMT-004.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
