<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-MGMT-007 — CRUD 五错误分支与资源版本迁移

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-MGMT-007` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-MGMT-007.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-MGMT-007`）；责任摘要、分类与优先级以 [模块测试方案 §3](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-MGMT-007.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-MGMT-007` / M004 CRUD 错误分支：412/409-conflict/409-in-use/404/400 provider_id（组装） v0.1.0-draft.3 / VRC-MGMT-002（management-design §14 / management.isd §9.1，management 0.1.0-draft.3） / VRC-MGMT-002 / negative / P0（[方案清单 §3](../llmtier-module-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（非法字段/凭据/引用/类型/顺序）+ 判定表组合（主要手段：无边界替身，全真实（仅 ENV-1/ENV-2 真实实现））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M004-CRUD 五错误分支；组合：K6、K6；迁移：T8、T8
- 要测什么（责任展开）：ETag stale 412；UNIQUE 409 `resource_conflict`；删除被引用 409 `resource_in_use`；未知 404；deployment provider_id 变更 400（本 Case 责任：K6 组合行全覆盖（412/409-conflict/409-in-use/404/400）；T8 版本 vN→vN+1 且旧 ETag 失效）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝management 组装后CRUD 错误矩阵与版本迁移与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`registry.py::update_provider`/`update_deployment`/`update_service_level`/`delete_*`、`app.py` 资源路由

```text
update_*(rid, body, if_match); delete_*(rid, if_match)
```

- 初态构造（经公开入口）：`AppFixture` + `seed()`（ENV-1）+ ENV-2；ETag 取自 `GET` 响应头
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-2
- 依赖的测试资产（tests.asset-design 文档）：组装夹具 `tests/common/fakes.py::AppFixture`（见 `llmtier-unit-fakes`）

## 3. 输入构造

- 逐参数输入构造：provider/deployment 各两次 PATCH（第二次用旧 ETag）；重复 `POST /v1/service-levels`（成员合法）；删除被引用 provider/deployment；未知资源三形态；重名创建；deployment `provider_id` 变更；空成员 tier 创建
- 边界/非法取值及理由：412（provider/deployment）→`version_conflict`；409 冲突 `resource_conflict` 与被引用 `resource_in_use`；404 `not_found`；`provider_id` 变更→400（`param=provider_id`）；空成员→400（`param=deployment_ids`）；T8 版本单调且旧 ETag 失效
- 规模 / 时间域（数量、分页、复杂度、观测开销）：10 请求；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | provider 旧 ETag PATCH | 412 `version_conflict` |
| 2 | deployment 旧 ETag PATCH | 412 |
| 3 | 重复创建已存在 tier（成员合法） | 409 `resource_conflict` |
| 4 | 删除被引用 provider / deployment | 均 409 `resource_in_use` |
| 5 | 未知 provider PATCH / deployment DELETE / tier GET | 均 404 `not_found` |
| 6 | 重名创建 provider | 409 `resource_conflict` |
| 7 | 版本推进 | `version` 1→2，新 ETag `"<id>.v2"` |
| 8 | deployment 改 `provider_id` | 400 `invalid_request`，`param=provider_id` |
| 9 | tier 空成员创建 | 400 `invalid_request`（`deployment_ids`） |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：方案 §3.3 K6 + §3.4 T8 + management 模块设计 §14.2；按各 CRUD 方法的 `raise` 顺序与 `_etag` 格式人工推导
- 互斥预期（成功 / 各错误分支）：K6 组合行全覆盖；错误码与 `param` 精确；版本迁移单调且旧 ETag 失效

## 6. 错误路径、副作用与清理

- 错误出口与表现：412/409/404/400 四类码精确
- 副作用断言与清理：被拒变更不落库；版本号只增不减

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-MGMT-007.py`（9 个）：`test_provider_stale_etag_412`、`test_deployment_stale_etag_412`、`test_service_level_duplicate_conflict_409`、`test_service_level_empty_members_is_400`、`test_provider_in_use_409`、`test_deployment_in_use_409`、`test_unknown_resources_are_404`、`test_version_transitions_and_provider_id_immutable`、`test_duplicate_names_are_409_conflict`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-MGMT-007.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
