<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-PROV-003 — 获取 provider 详情

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-PROV-003` |
| Document Version | `0.1.0-draft.3` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-29` |
| Last Modified Date | `2026-10-01` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `native` |
| Tailoring Reference | none |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/cases/ST-PROV-003.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-PROV-003`）；责任摘要、分类与优先级以 [系统测试方案 §3](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 Provider CRUD 接口（/v1/providers）（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-001`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-PROV-003` 可追到方案清单行与 Run 报告。

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-PROV-003` / 系统设计 §8 Provider CRUD 接口（/v1/providers） / `VRC-MGMT-001` / `normal` / `P0`
- **测试方法（§1.5 方法表行）**：等价类划分 + 契约字段比对
- 方案清单登记：`ST-PROV-003`（与 §3.2 权威清单一致；本文件名 `st-prov-003.md`，唯一对应）。
- 要测什么（责任展开）：`GET /v1/providers/{id}` 读取已存在 provider 详情：HTTP 200 + `ProviderView` 全字段 + `ETag` 响应头，纯读。
- 明确不测什么 / 失败含义：不证明 列表（ST-PROV-001）、不证明创建/更新/删除（ST-PROV-002/05..10）、不证明不存在 404 的完整负向（ST-PROV-004）、不证明 `usage` 子对象可写（ST-PROV-013）、不证明响应不含 secret 的强断言（ST-PROV-014）；`request_usage` 的具体计数依赖历史 usage，本 case 只断言字段存在与类型。

**目的（被测契约）**：验证 Management Provider CRUD 的**详情读契约**。被测端点/规则：`GET /v1/providers/{id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `getProvider`，`security=AdminBearerAuth`），认证角色 `admin`；成功 `200` + body `ProviderView{id,name,kind,endpoint,has_secret,enabled,usage,request_usage,version}` + 响应头 `ETag: "<id>.v<N>"`；失败走统一错误信封（404 `not_found`）。设计验证项 `VRC-MGMT-001`；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`T-CFG-CAS`、`CT-ADMIN-001`（[系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）。**不证明什么**：不证明列表（ST-PROV-001）、不证明创建/更新/删除（ST-PROV-002/05..10）、不证明不存在 404 的完整负向（ST-PROV-004）、不证明 `usage` 子对象可写（ST-PROV-013）、不证明响应不含 secret 的强断言（ST-PROV-014）；`request_usage` 的具体计数依赖历史 usage，本 case 只断言字段存在与类型。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例；角色 `admin`，只读；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）。执行前必须通过[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go)(../llmtier-system-test-scheme.md) 的 6 项就绪检查（详见 §2.1）；任一失败 → 整班 BLOCKED/SKIP，不得改用模拟路径。fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）：`admin_client`。初始状态：m5air 现有 3 provider / 4 deployment / 7 tier；本 case 固定读取 `provider_local`（§2.1.6 保证存在）。

## 3. 输入构造

- **输入与构造**：固定请求（无请求体、无查询参数）：
  ```http
  GET /v1/providers/provider_local HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：`{id}` 固定为就绪检查保证存在的 `provider_local`；无 body；不注入故障；不构造非法输入（不存在 id 属 ST-PROV-004）。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（`pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = admin_client.get("/v1/providers/provider_local")`；记录 status、headers、body。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`。
  4. 解析 body：断言必填字段全在 `{id,name,kind,endpoint,has_secret,enabled,usage,request_usage,version}`；`id == "provider_local"`；`kind ∈ {cloud,local}`；`has_secret`/`enabled` 为 JSON 布尔；`version` 为正整数；`usage` 为 `ProviderUsageProfileView`（含 `usage_provider`、`max_concurrent_requests` 等）；`request_usage` 为 `{calls,input_tokens,output_tokens,total_tokens}`。
  5. 断言响应头含 `ETag`，格式匹配 `"provider_local.v<N>"`（含双引号）。
  6. 断言 body 不含顶层 `secret_ref` 键、不含解析后的 secret 值（与 ST-PROV-014 一致的读路径，此处为旁证）。

**重点关注步骤**：① **字段完整性**——`ProviderView` 为 `additionalProperties:false` 且必填 9 键，缺键/多键即 FAIL；② **类型精确性**——`has_secret`/`enabled` 为布尔、`version` 为整数；③ **ETag 格式**——必须 `"<id>.v<N>"` 含双引号（`_etag`），不是裸 `id.vN`；④ **纯读、无副作用**——详情路径不写库、不铸分页快照（与列表 ST-PROV-001 不同）；⑤ **不依赖 usage 数值**——`request_usage` 计数随历史变化，只断言结构与类型；⑥ **不得把错误信封当详情**——非 200 需先确认是可解释的 `ERR-AUTH-*`/`ERR-NOTFOUND`。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ProviderView` wire 形态 + ETag 规则（不依赖 m5air 数据）。
  - HTTP：`200`；`Content-Type: application/json`；响应头 `ETag: "provider_local.v<N>"`。
  - body：`ProviderView` 9 必填键齐备且类型正确；`id=="provider_local"`；无 `secret_ref` 键、无 secret 值。
  - 无错误信封：成功路径不应出现 `{"error":{...}}`。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==200` 且 9 必填键齐备、类型正确、`id=="provider_local"`、ETag 格式匹配。
  - **FAIL**：status 非 200 且资源健康，或字段缺失/类型错/ETag 不符，或响应回显 `secret_ref`/secret 值。
  - **BLOCKED**：测试代码/契约本身问题（断言不可实现、语义不清）——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足（含 `provider_local` 未注册）——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——纯读，不改 provider/deployment、不写注入、不铸分页快照。退出前确认 `/readyz` 仍 7 tier、无未清空注入项；若误跑于 B 类实例，则按[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md) 整班 `stop()` + `rm -rf`。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)(../llmtier-system-test-scheme.md)：Run ID=`<date>/A-api`；保存原始 status/headers/body（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。

- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查（含 `provider_local` 注册）；`admin_client` fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）；`ProviderView` 机器契约；自动化入口 [`ST-PROV-003.py`](../../../../tests/system/cases/ST-PROV-003.py)。**不依赖**其它 Case；与 ST-PROV-004（不存在 → 404）成对但各自独立。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
