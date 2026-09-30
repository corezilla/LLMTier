<!-- STD_DOCUMENT_COVER_BEGIN -->
# ADM-DEPL-03 — 获取 deployment

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ADM-DEPL-03` |
| Document Version | `0.1.0-draft.2` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-29` |
| Last Modified Date | `2026-09-30` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `native` |
| Tailoring Reference | none |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/specifications/cases/adm-depl-03.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ADM-DEPL-03`）；责任摘要、分类与优先级以 [系统测试方案 §3](../../schemes/llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 Deployment CRUD 接口（/v1/deployments）（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-001`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ADM-DEPL-03` 可追到方案清单行与 Run 报告。

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ADM-DEPL-03` / 系统设计 §8 Deployment CRUD 接口（/v1/deployments） / `VRC-MGMT-001` / `normal` / `P0`
- 方案清单登记：`ADM-DEPL-03`（与 §3.2 权威清单一致；本文件名 `adm-depl-03.md`，唯一对应）。
- 要测什么（责任展开）：`GET /v1/deployments/{id}` 读取既存 deployment：HTTP 200 + `DeploymentView` + `ETag`，纯读、无副作用。
- 明确不测什么 / 失败含义：不证明 列表（ADM-DEPL-01）、不证明创建/更新/删除（ADM-DEPL-02/04/05）、不证明未知 id 的 404（本 case 只读既存 `dep_local_gemma`）、不证明 `capabilities` 校验（ADM-DEPL-06/07）；本 case 只读、不触上游。

**目的（被测契约）**：验证 Management Deployment CRUD 的**详情读契约**。被测端点/规则：`GET /v1/deployments/{deployment_id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `getDeployment`，`security=AdminBearerAuth`），认证角色 `admin`；成功 `200` + `DeploymentView`（`id,name,provider_id,backend_model,capabilities,enabled,health,version`，`additionalProperties:false`）+ 响应头 `ETag: "<id>.v<N>"`（[`registry.get_deployment`](../../../../src/management/registry.py)）；未知 id → 404 `not_found`；失败走统一错误信封（401/403）。设计验证项 `VRC-MGMT-001`；需求/机制链 `LT-FUN-005`、`LT-INT-008`、`R-CFG-01`、`CT-ADMIN-001`（[系统测试方案 §3 覆盖分母与 Case 清单](../../schemes/llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）。**不证明什么**：不证明列表（ADM-DEPL-01）、不证明创建/更新/删除（ADM-DEPL-02/04/05）、不证明未知 id 的 404（本 case 只读既存 `dep_local_gemma`）、不证明 `capabilities` 校验（ADM-DEPL-06/07）；本 case 只读、不触上游。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例；角色 `admin`，只读；见[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）。执行前必须通过[系统测试计划 §3 执行前检](../../plans/llmtier-system-test-plan.md#3-执行前检go--no-go)(../../schemes/llmtier-system-test-scheme.md) 的 6 项就绪检查（详见 §2.1）；任一失败 → 整班 BLOCKED/SKIP，不得改用模拟路径。fixture（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）：`admin_client`。初始状态：m5air 现有 3 provider / 4 deployment / 7 fixed tier；被测 deployment 取 §2.1.6 必需的 `dep_local_gemma`（必在）。

## 3. 输入构造

- **输入与构造**：固定请求（无请求体、无查询参数）：
  ```http
  GET /v1/deployments/dep_local_gemma HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：`{deployment_id}` 固定为既存 `dep_local_gemma`；无 body、无 query；不注入故障；不构造非法输入（未知 id 属其它负向 case）。`version`/`health` 值与运行状态有关，只断言字段存在与类型。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = admin_client.get("/v1/deployments/dep_local_gemma")`；记录 status、headers、body。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`。
  4. 解析 body：断言键集恰为 `DeploymentView` 的 8 键；`body["id"] == "dep_local_gemma"`、`name/provider_id/backend_model` 为字符串、`enabled` 为布尔、`version` 为正整数、`health ∈ {unknown,healthy,degraded,unhealthy}`。
  5. 断言 `body["capabilities"]` 键集恰为 12 键（`ModelCapabilities`）。
  6. 断言响应头含 `ETag` 且匹配 `^"[A-Za-z0-9._:-]+"$`，且等于 `f'"{body["id"]}.v{body["version"]}"'`。

**重点关注步骤**：① **字段集精确性**——键集恰为 8 键，多/少一键违反 `additionalProperties:false`；② **`capabilities` 12 键**——详情元素也须满足全集；③ **ETag 与 version 一致**——`ETag == "<id>.v<version>"`（含双引号），这是后续 PATCH/DELETE 的前置；④ **纯读**——GET 不写任何资源（`get_deployment` 只 SELECT）；⑤ **不硬编码 version/health**——随运行变化，只断言类型/枚举与 ETag 一致性；⑥ **不得把错误信封当详情**——非 200 需先确认是可解释的 `ERR-AUTH-*`/`ERR-NOTFOUND`。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `DeploymentView` + ETag 格式（不依赖 m5air 运行态）。
  - HTTP：`200`；`Content-Type: application/json`；响应头 `ETag=="<id>.v<version>"`。
  - body：键集恰 8 键；`id=="dep_local_gemma"`；`capabilities` 12 键；`health` 属枚举。
  - 无错误信封。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==200` + 8 键 `DeploymentView` + `capabilities` 12 键 + `id` 匹配 + `ETag` 与 version 一致。
  - **FAIL**：status 非 200 且资源存在/鉴权健康，或键集/类型/`capabilities`/ETag 不符。
  - **BLOCKED**：测试代码/契约本身问题——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足（`dep_local_gemma` 未注册等）——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用替代路径/伪造详情冒充——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——本 case 为纯读，不改 deployment/provider/service-level、不写注入。退出前确认 `/readyz` 7 tier、deployment 列表未变、无未清空注入；若误跑于 B 类实例，则整班 `stop()` + `rm -rf`。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[系统测试计划 §6 证据与 Run 记录规则](../../plans/llmtier-system-test-plan.md#6-证据与-run-记录规则)(../../schemes/llmtier-system-test-scheme.md)：Run ID=`<date>/A-api`；保存原始 status/headers/body（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。**本 case 额外证据**：`inputs` 含 `deployment_id`。

- **依赖**：[系统测试计划 §3 执行前检](../../plans/llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查（含 §2.1.6 必需 deployment）；`admin_client` fixture（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）；既存 deployment `dep_local_gemma`；`DeploymentView` 机器契约；实现 `src/management/registry.py` `get_deployment`；自动化入口 [`at_adm_depl_03.py`](../../../../tests/system/api_test_v03/at_adm_depl_03.py)。**不依赖**其它 Case；与 ADM-DEPL-01 共享读路径但各自独立执行。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
