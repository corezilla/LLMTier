<!-- STD_DOCUMENT_COVER_BEGIN -->
# MT-API-006 — `_auth` 三态与 `_auth_either` 优先级

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `MT-API-006` |
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
| Canonical Path | `docs/70_verification/module/cases/MT-API-006.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`MT-API-006`）；责任摘要、分类与优先级以 [模块测试方案 §6](../llmtier-module-test-scheme.md) 清单行为准，不在本文档重复维护。
- **测试脚本的唯一依据**：编码者按本文档写测试代码；§7 指向已实现脚本 `tests/module/cases/MT-API-006.py`。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`MT-API-006` / M001 `_auth` 三态 401/403/503 + `_auth_either` 优先级（组装） v0.1.0-draft.2 / VRC-API-002（http-api-design §14 / http-api.isd §9.1，http-api 0.1.0-draft.2） / VRC-API-002 / security / P0（[方案清单 §6](../llmtier-module-test-scheme.md)）。
- **测试方法（§2.4 方法表行）**：鉴权/脱敏/注入边界冒烟 + 契约 + 分支×端点配对（主要手段：无边界替身，全真实（仅 ENV-1/ENV-2 真实实现））
- **覆盖的分支 / 组合 / 迁移 ID**：分支：M001-401/403/503 / `_auth_either` 优先级；组合：K1
- 要测什么（责任展开）：缺失配置→503 `auth_not_configured`；无 Bearer→401；错误凭据→403；`_auth_either` admin-first 且 401 与 403 不泄露存在性（本 Case 责任：未配置→503/无 Bearer→401/错误凭据→403；`_auth_either` admin 先于 data 且不泄露存在性）
- 明确不测什么 / 失败含义：不测跨模块系统级流程、真实上游 provider 协议、浏览器 E2E（归系统层 `ST-*` 与契约层）；本层只断言组装后成立的分支走向、状态迁移与调用序。失败含义＝http-api 组装后鉴权三态与共享端点优先级与设计不一致。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/http_api/auth.py::authenticate`/`authenticate_any`/`unauthenticated_principal`、`app.py::Handler._auth`/`_auth_either`

```text
GET /v1/models, /v1/providers, /v1/usage (GET/DELETE) with/without Authorization
```

- 初态构造（经公开入口）：同 MT-API-001；凭据配置经进程环境变量注入（`LLMTIER_ADMIN_TOKEN`/`LLMTIER_DATA_TOKEN`）
- 环境类型 + ENV 实例编号（引用 [模块测试计划 §4](../llmtier-module-test-plan.md) 分配）：ENV-1 + ENV-2（+ 进程环境配置）
- 依赖的测试资产（tests.asset-design 文档）：无（全部真实实现；不经替身）

## 3. 输入构造

- 逐参数输入构造：无 `Authorization`；`Basic abc`；`Bearer nope`；正确的 admin/data Bearer；`/v1/usage` DELETE 对比 admin/data
- 边界/非法取值及理由：未配置+Bearer→503；非 Bearer→401；错值→403；`_auth_either` admin-first，data 角色 DELETE→403
- 规模 / 时间域（数量、分页、复杂度、观测开销）：7 请求；O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 无 `Authorization` 访问 `/v1/models` | 200（loopback 受信） |
| 2 | 两 token 置空 + `Bearer anything` | 503 `auth_not_configured` |
| 3 | 配置 admin token + `Basic abc` | 401 `authentication_required` |
| 4 | 配置 admin token + `Bearer nope` | 403 `permission_denied` |
| 5 | 两 token 均配置，admin/data 各自 `GET /v1/usage` | 均 200（角色不同：data 视图受限） |
| 6 | admin token `DELETE /v1/usage` | 200 |
| 7 | data token `DELETE /v1/usage` | 403 `permission_denied` |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：http-api 模块设计 §14.2 + ISD 鉴权契约；按 `authenticate`/`authenticate_any` 的三处 `raise` 人工推导
- 互斥预期（成功 / 各错误分支）：401/403/503 三态互斥；401 与 403 不泄露资源存在性；`_auth_either` admin-first

## 6. 错误路径、副作用与清理

- 错误出口与表现：未配置 503 / 非 Bearer 401 / 错值 403 / data 角色越权 403
- 副作用断言与清理：拒绝发生在业务之前，不产生写副作用

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/module/cases/MT-API-006.py`（6 个）：`test_bearer_without_config_is_503_auth_not_configured`、`test_non_bearer_authorization_is_401`、`test_wrong_bearer_is_403`、`test_loopback_without_authorization_is_trusted`、`test_admin_first_on_shared_endpoint`、`test_unauthenticated_on_shared_endpoint_is_401_with_malformed_header`
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/module/cases/MT-API-006.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/module/cases`）；执行状态与 Verdict 见 Run 报告 `tests/module/reports/<run-id>/`。

<!-- 交付自查：编码者能否只凭本文档写出测试脚本；预期是否独立推导（不调用被测实现复算）；失败出口与清理是否可观察？ -->
