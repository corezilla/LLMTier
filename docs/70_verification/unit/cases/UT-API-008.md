<!-- STD_DOCUMENT_COVER_BEGIN -->
# UT-API-008 — 分发层鉴权角色与 admin-first 选择

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `UT-API-008` |
| Document Version | `0.1.0-draft.2` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-30` |
| Last Modified Date | `2026-10-01` |
| Template ID | `tests.unit-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/unit/cases/UT-API-008.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`UT-API-008`）；责任摘要、分类与优先级以 [单元测试方案 §3](../llmtier-unit-test-scheme.md) 清单行为准。
- **来源**：模块设计 [http-api](../../../40_module_design/http-api-design.md) §14 / ISD [http-api.isd.md](../../../50_implementation_design/http-api.isd.md) §9.1，设计验证项 `VRC-API-002`（固定版本 `http-api 0.1.0-draft.2`）。
- **裁剪说明**：本 Case 是项目级合并方案 `llmtier-unit-test-scheme` 的模块切片 `http_api`；裁剪依据见 [STD 裁剪清单](../../../00_management/std-tailoring.md)。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `UT-API-008` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`UT-API-008` / M001 http-api §14.2 · `authorize` 角色选择 v0.1.0-draft.2 / `VRC-API-002` / security / P0（[方案清单 §3](../llmtier-unit-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：鉴权/脱敏/注入边界冒烟（角色选择/401）（主要手段：直接调用 + 冻结向量 + 替身注入）
- 要测什么（责任展开）：被测：data 凭据访问 admin 端点 → 403（分发层 `_auth("admin")`）；admin 凭据访问 admin 端点 → 200；`_auth_either` 的 admin-first 角色选择；**非受信来源（合成公网地址如 `8.8.8.8`）无 `Authorization` 头 → 401 `authentication_required`**（`unauthenticated_principal` 返回 `None` 后 `authenticate` 抛 401；系统层 A/B 无法构造非受信来源，故在此单元承接）。
- 明确不测什么 / 失败含义：不测：信任地址免登录（UT-API-002）；不测深层安全。失败含义＝分发层角色判定或 403 实现错误。

## 2. 被测入口与前置

- 被测入口声明与位置：`src/http_api/app.py::Handler._auth`（role="admin"）与 `Handler._auth_either`；`src/http_api/auth.py::authenticate_any`

```text
Handler._auth(role="data"); Handler._auth_either() -> (Principal, is_admin)
```

- 初态构造（经公开入口）：`AppFixture` 配置鉴权 token，起 loopback 实例（ENV-2）
- Fixture / 向量及版本：`tests/common/fakes.py::AppFixture`（ENV-1）+ `UT-API-008.py::AdminDispatchAuthTests`（ENV-2）
- 环境类型 + ENV 实例编号（引用 [单元测试计划 §4](../llmtier-unit-test-plan.md) 分配）：ENV-2 loopback 测试 HTTP 实例
- 依赖的测试资产（tests.asset-design 文档）：无（真实实现）

## 3. 输入构造

- 逐参数输入构造：`Authorization: Bearer <data-token>` 访问 admin 端点；`Bearer <admin-token>` 访问同一端点
- 边界/非法取值及理由：正确角色 200 / 错误角色 403（二态互斥）；401 与 403 不泄露存在性
- 规模 / 时间域（数量、分页、复杂度、观测开销）：单请求，O(1)

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | data token 访问 admin 端点 | 403 |
| 2 | admin token 访问 admin 端点 | 200 |
| 3 | 校验角色选择为 admin-first | 双 token 配置下经 `/v1/usage` DELETE 驱动：admin token→200、data token→403 |
| 4 | 非受信地址（`8.8.8.8`）无 `Authorization` 头 | `unauthenticated_principal`→`None`；`authenticate`→401 `authentication_required` |

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：T-API-02/03 授权顺序 + `CON-TRUST-001` + 人工推导；不调用被测复算。**判据语义以设计验证项 `VRC-API-002` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：data→admin 端点 403；admin→admin 端点 200；401/403 不可区分资源存在性；互斥

## 6. 错误路径、副作用与清理

- 错误出口与表现：403（角色不足）；无第三态
- 副作用断言与清理：无（鉴权失败不落业务库）；loopback 实例清理

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/unit/cases/UT-API-008.py::AdminDispatchAuthTests::test_data_token_on_admin_endpoint_is_403` / `test_admin_token_on_admin_endpoint_is_200` / `test_auth_either_admin_first_role_selection`（双 token 配置下经 `/v1/usage` DELETE 驱动 `_auth_either` admin-first 角色选择：admin token→200、data token→403）；角色选择另由 `UT-API-008.py::test_admin_token`/`test_principal_header` 覆盖；**非受信来源缺凭据 401** 由 `UT-API-008.py::test_non_trusted_address_without_credential_is_401` 覆盖（系统层 ST-AUTH-010 以非法授权方案触发同一 401 分支；非受信来源无系统级构造）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/unit/cases/UT-API-008.py -q`
- 实现状态：`Implemented`（测试函数已存在于 `tests/unit/cases/UT-API-008.py`）；执行状态与 Verdict 见 Run 报告 `run-20261001-04`。
