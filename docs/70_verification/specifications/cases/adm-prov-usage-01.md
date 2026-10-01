<!-- STD_DOCUMENT_COVER_BEGIN -->
# ADM-PROV-USAGE-01 — 读取 provider usage 快照

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ADM-PROV-USAGE-01` |
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
| Canonical Path | `docs/70_verification/specifications/cases/adm-prov-usage-01.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ADM-PROV-USAGE-01`）；责任摘要、分类与优先级以 [系统测试方案 §3](../../schemes/llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 provider usage 快照接口（/v1/providers/{id}/usage）（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-006`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ADM-PROV-USAGE-01` 可追到方案清单行与 Run 报告。

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ADM-PROV-USAGE-01` / 系统设计 §8 provider usage 快照接口（/v1/providers/{id}/usage） / `VRC-MGMT-006` / `normal` / `P1`
- **测试方法（§1.5 方法表行）**：等价类划分 + 契约字段比对
- 方案清单登记：`ADM-PROV-USAGE-01`（与 §3.2 权威清单一致；本文件名 `adm-prov-usage-01.md`，唯一对应）。
- 要测什么（责任展开）：`GET /v1/providers/{id}/usage` 读取 provider 账号用量快照：HTTP 200 + 精确 `ProviderAccountUsageSnapshot`（12 个必填键），纯读、无副作用。
- 明确不测什么 / 失败含义：不证明 刷新（ADM-PROV-USAGE-02/03）、不证明未知 provider 的 404（ADM-PROV-USAGE-04）、不证明上游用量 API 的真实数值正确性（上游决定，本 case 只断言 wire 形状与枚举）、不证明 provider 详情/secret 不泄露（ADM-PROV-14）。

**目的（被测契约）**：验证 Management **provider 账号用量快照读契约**。被测端点/规则：`GET /v1/providers/{provider_id}/usage`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `getProviderAccountUsage`，`security=AdminBearerAuth`），认证角色 `admin`；成功 `200` + `ProviderAccountUsageSnapshot`（`additionalProperties:false`，`required` 恰 12 键：`provider,source,status,used,quota,remaining,percent,reset_at,window,windows,checked_at,error`；`status ∈ {ok,unavailable,unsupported,unlimited,not_refreshed}`）；失败走统一错误信封（401 `authentication_required` / 403 `permission_denied` / 404 `not_found`）。实现见 [`AccountUsageService.latest`](../../../../src/management/account_usage.py)（先查 `provider_usage_snapshots`，无快照则按 usage profile 合成 `not_refreshed`/credentials 快照）。设计验证项 `VRC-MGMT-006`；需求/机制链 `LT-FUN-005/006`、`LT-OPS-002`、`R-CFG-01`、`R-OBS-01`、`T-CFG-SECRET`、`CT-ADMIN-001`/`CT-OPS-001`（[系统测试方案 §3 覆盖分母与 Case 清单](../../schemes/llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）。**不证明什么**：不证明刷新（ADM-PROV-USAGE-02/03）、不证明未知 provider 的 404（ADM-PROV-USAGE-04）、不证明上游用量 API 的真实数值正确性（上游决定，本 case 只断言 wire 形状与枚举）、不证明 provider 详情/secret 不泄露（ADM-PROV-14）。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例；角色 `admin`，只读；见[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）。执行前必须通过[系统测试计划 §3 执行前检](../../plans/llmtier-system-test-plan.md#3-执行前检go--no-go)(../../schemes/llmtier-system-test-scheme.md) 的 6 项就绪检查（详见 §2.1）；任一失败 → 整班 BLOCKED/SKIP，不得改用模拟路径。fixture（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）：`admin_client`。初始状态：m5air 现有 3 provider / 4 deployment / 7 fixed tier；被测 provider 取 §2.1.6 必需的 `provider_local`。**注意状态依赖**：若同轮更早执行了 ADM-PROV-USAGE-03（刷新），则 `provider_usage_snapshots` 已存在该 provider 的快照，GET 返回刷新后的快照（`provider_local` 为 local，`status="unlimited"`、`source="quota_config"`）；否则返回合成快照（`status="not_refreshed"`、`source="store"`）。两者均 PASS，**不得**对具体 `status`/`source`/时间值做硬断言。

## 3. 输入构造

- **输入与构造**：固定请求（无请求体、无查询参数；`{id}` 取 `provider_local`）：
  ```http
  GET /v1/providers/provider_local/usage HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：`provider_id` 固定为既存 `provider_local`；**无 body**、**无 query**（该端点不接受参数，不触上游——`GET` 只读已持久化/合成的快照）；不注入故障；不构造非法输入。**时间/窗口值动态**：`checked_at`/`reset_at`/`windows` 为运行时或上游值，Oracle 只约束结构与类型。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = admin_client.get("/v1/providers/provider_local/usage")`；记录 status、`Content-Type`、原始 body。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`。
  4. 解析 body，断言其为对象且键集**恰为** `ProviderAccountUsageSnapshot` 的 12 键（不多不少）。
  5. 断言 `status` 属于枚举 `{ok,unavailable,unsupported,unlimited,not_refreshed}`；`provider`/`source`/`window`/`reset_at`/`checked_at`/`error` 为字符串；`used`/`quota`/`remaining`/`percent` 为 number 或 `null`；`windows` 为数组（元素为对象）。
  6. （交叉核对，不改变判定）`GET /v1/providers/provider_local` 断言 `200` 且 `id=="provider_local"`，佐证快照归属的 provider 存在。

**重点关注步骤**：① **字段集精确性**——不是"含 provider/status"，而是"键集恰为 12 键"，多/少一键即违反 `additionalProperties:false`；② **枚举约束**——`status` 只允许 5 个值之一，不能是任意字符串；③ **纯读、无副作用**——GET 不刷新、不触上游、不写 `provider_usage_snapshots`（刷新仅在 ADM-PROV-USAGE-03 的 POST）；④ **禁止硬编码动态值**——`checked_at`/`reset_at`/`windows`/`status` 随运行与上游变化，不得写成固定时间或固定 `ok`；  ⑤ **不得被错误信封冒充**——非 200 需确认是可解释的 `ERR-AUTH-*`/`ERR-NOTFOUND`，而非把 `{error:...}` 当快照读。
  > **脚本覆盖（已补齐）**：现有 [`at_adm_prov_usage_01.py`](../../../../tests/system/api_test_v03/at_adm_prov_usage_01.py) 已断言键集**恰为** `ProviderAccountUsageSnapshot` 的 12 键、`status` 枚举，以及各字段类型（字符串/number|null/数组）；与 §4 step 4/5 一致。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ProviderAccountUsageSnapshot` wire 形态（不依赖 m5air 具体快照值）。
  - HTTP：`200`；`Content-Type: application/json`。
  - body：JSON 对象，键集**恰为** 12 键；`status` ∈ 枚举；数字字段为 number/`null`；`windows` 为数组（元素对象）。
  - 无错误信封。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==200` 且 body 键集恰为 12 键、`status` 属枚举、各字段类型符合 schema（`provider_local` 既不要求特定 `status` 也允许 `not_refreshed`/`unlimited`）。
  - **FAIL**：status 非 200 且存储健康；或键集不符、`status` 非枚举、字段类型错；或以错误信封冒充快照。
  - **BLOCKED**：无法执行/无法判定且可重试（fixture/断言逻辑问题）——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足（m5air 不可达、`provider_local` 未注册等）——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或伪造快照——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`；不得以未跑冒充 PASS。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——本 case 为纯读，不刷新快照、不改 provider/deployment/service-level、不写注入。退出前确认 `/readyz` 仍显示 7 tier、provider 列表未变、无未清空注入项；若被误跑于 B 类临时实例，则按[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md) 整班 `stop()` + `rm -rf` 临时目录。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[系统测试计划 §6 证据与 Run 记录规则](../../plans/llmtier-system-test-plan.md#6-证据与-run-记录规则)(../../schemes/llmtier-system-test-scheme.md)：Run ID=`<date>/A-api`；保存原始 status/headers/body（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。**本 case 额外证据**：`inputs` 与原始响应。

- **依赖**：[系统测试计划 §3 执行前检](../../plans/llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查（含 §2.1.6 必需 provider）；`admin_client` fixture（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）；既存 provider `provider_local`；`ProviderAccountUsageSnapshot` 机器契约（`interfaces/openapi/llmtier.openapi.json`）；实现 `src/management/account_usage.py`；自动化入口 [`at_adm_prov_usage_01.py`](../../../../tests/system/api_test_v03/at_adm_prov_usage_01.py)。**不依赖**其它 Case；与 ADM-PROV-USAGE-02/03（POST 确认路径）、ADM-PROV-USAGE-04（未知 provider 404）语义相邻但各自独立执行。

> 实现状态：Implemented（[`at_adm_prov_usage_01.py`](../../../../tests/system/api_test_v03/at_adm_prov_usage_01.py)）；执行状态与 Verdict 只在 Run 报告。
