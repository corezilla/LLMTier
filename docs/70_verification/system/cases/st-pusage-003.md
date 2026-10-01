<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-pusage-003 — 刷新带确认

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-pusage-003` |
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
| Canonical Path | `docs/70_verification/system/cases/st-pusage-003.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-pusage-003`）；责任摘要、分类与优先级以 [系统测试方案 §3](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 provider usage 快照接口（/v1/providers/{id}/usage）（parent `llmtier-system-design`），设计验证项 ``VRC-MGMT-006`、`VRC-DIAG-004``；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-pusage-003` 可追到方案清单行与 Run 报告。

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-pusage-003` / 系统设计 §8 provider usage 快照接口（/v1/providers/{id}/usage） / ``VRC-MGMT-006`、`VRC-DIAG-004`` / `normal` / `P1`
- **测试方法（§1.5 方法表行）**：等价类划分 + 契约字段比对
- 方案清单登记：`ST-pusage-003`（与 §3.2 权威清单一致；本文件名 `st-pusage-003.md`，唯一对应）。
- 要测什么（责任展开）：`POST /v1/providers/{id}/usage` 携带 `{"confirm_external_call": true}` 刷新账号用量：HTTP 200 + 新 `ProviderAccountUsageSnapshot`；`provider_local`（local 类型）返回 `status="unlimited"`、`source="quota_config"`，并持久化快照。
- 明确不测什么 / 失败含义：不证明 缺确认拒绝（ST-pusage-002）、不证明只读快照（ST-pusage-001）、不证明未知 provider 的 404（ST-pusage-004）、不证明 minimax/volc 的真实上游用量数值（本 case 用 `provider_local`，其刷新为本地合成、不触外部用量 API，故**不产生费用**）；不证明并发刷新。

**目的（被测契约）**：验证 provider 账号用量**显式刷新成功契约**。被测端点/规则：`POST /v1/providers/{provider_id}/usage`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `refreshProviderAccountUsage`，`security=AdminBearerAuth`），请求体 `{confirm_external_call: true}`（键集必须恰为 `{confirm_external_call}`）；成功 `200` + `ProviderAccountUsageSnapshot`，并按 `usage_provider` 分流：`local` → `_snapshot("local","quota_config","unlimited")`（[`AccountUsageService.refresh`](../../../../src/management/account_usage.py)），写 `provider_usage_snapshots`（`ON CONFLICT DO UPDATE`）；失败 400 `invalid_request`/`confirmation_required`、404 `not_found`。设计验证项 `VRC-MGMT-006`、`VRC-DIAG-004`；需求/机制链 `LT-FUN-005/006`、`LT-OPS-002`、`R-CFG-01`、`R-OBS-01`、`T-CFG-SECRET`、`CT-ADMIN-001`/`CT-OPS-001`（[系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）。**不证明什么**：不证明缺确认拒绝（ST-pusage-002）、不证明只读快照（ST-pusage-001）、不证明未知 provider 的 404（ST-pusage-004）、不证明 minimax/volc 的真实上游用量数值（本 case 用 `provider_local`，其刷新为本地合成、不触外部用量 API，故**不产生费用**）；不证明并发刷新。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例；角色 `admin`，；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）。执行前必须通过[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go)(../llmtier-system-test-scheme.md) 的 6 项就绪检查（详见 §2.1）；任一失败 → 整班 BLOCKED/SKIP，不得改用模拟路径。fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）：`admin_client`。初始状态：m5air 现有 3 provider / 4 deployment / 7 fixed tier；被测 provider 取 §2.1.6 必需的 `provider_local`（local 类型 → 刷新为本地 `unlimited` 快照，不触费用）。执行前记录 `GET /v1/providers/provider_local/usage` 的原快照（`checked_at`），用于复位核对。

## 3. 输入构造

- **输入与构造**：带确认刷新请求：
  ```http
  POST /v1/providers/provider_local/usage HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Content-Type: application/json
  ```
  ```json
  {"confirm_external_call": true}
  ```
  构造点：body 键集**恰为** `{confirm_external_call}`、值为布尔 `true`；provider_id 固定为既存 `provider_local`；不注入故障；不构造非法输入。**值动态**：`checked_at` 为刷新时刻（动态），`windows`/`reset_at` 为实例/上游值，Oracle 只约束结构与 local 臂的枚举值。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. 记录原快照：`before = admin_client.get("/v1/providers/provider_local/usage")`；记 `before.json()`（用于复位核对与证据）。
  3. `resp = admin_client.post("/v1/providers/provider_local/usage", json={"confirm_external_call": True})`；记录 status、headers、body。
  4. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`。
  5. 解析 body：断言键集**恰为** `ProviderAccountUsageSnapshot` 的 12 键；`status ∈ {ok,unavailable,unsupported,unlimited,not_refreshed}`。
  6. 对 `provider_local`（local 类型）断言强值：`body["status"] == "unlimited"` 且 `body["source"] == "quota_config"`（`_snapshot("local","quota_config","unlimited")` 的确定输出）；若环境实际 kind 非 local，则退化为只断言 12 键 + 枚举（并在证据中记录 kind，作为偏差）。
  7. 回读：`after = admin_client.get("/v1/providers/provider_local/usage")`；断言 `200` 且 `after.json()["checked_at"] == resp.json()["checked_at"]`（刷新已持久化、GET 返回同一快照）。

**重点关注步骤**：① **确认是成功前提**——只有 body 键集恰 `{confirm_external_call}` 且值为 `true` 才到刷新分支（缺键/值非真属 ST-pusage-002）；② **local 臂的确定输出**——`provider_local` 为 local，刷新不触外部 API，`status="unlimited"`、`source="quota_config"` 可强断言；③ **持久化副作用**——刷新写 `provider_usage_snapshots`（`ON CONFLICT DO UPDATE`），第 7 步回读同 `checked_at` 证明落库，**必须登记该写入**；④ **值动态**——`checked_at` 动态，不得硬编码；⑤ **无费用**——local 臂不产生外部调用（与 minimax/volc 臂不同），报告须写明未触费用；  ⑥ **不把错误信封当快照**——非 200 需先确认是可解释的 `ERR-*`（缺键→`invalid_request`、值非真→`confirmation_required`、未知 provider→`not_found`）。
  > **脚本覆盖（已补齐）**：现有 [`at_adm_prov_usage_03.py`](../../../../tests/system/api_test_v03/at_adm_prov_usage_03.py) 已断言 12 键全集、`status` 枚举、local 臂 `unlimited`/`quota_config` 强值，并按 §4 step 7 回读 `GET .../usage` 断言 `checked_at` 与刷新响应一致（证明落库持久化）。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ProviderAccountUsageSnapshot` + `account_usage.refresh` 的 local 分流（不依赖上游）。
  - HTTP：`200`；`Content-Type: application/json`。
  - body：12 键全集；`provider_local` → `status=="unlimited"`、`source=="quota_config"`。
  - 回读：`GET .../usage` 返回相同 `checked_at` 的快照（持久化）。
  - 无错误信封。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`200` + 12 键快照 + local 臂 `status=="unlimited"`/`source=="quota_config"` + 回读 `checked_at` 一致。
  - **FAIL**：status 非 200、键集/枚举不符、local 臂值不符，或回读未持久化。
  - **BLOCKED**：无法执行/无法判定且可重试（fixture/断言逻辑问题）——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：伪造刷新响应、绕过真实确认键集，或替代路径冒充——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**一次性写，尽力复位**——本 case 刷新 `provider_local` 的 `provider_usage_snapshots` 行（替换旧快照）。该端点**没有** DELETE 接口，且按[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md) 不得删除 m5air 既有 provider/用户 usage；因此复位方式为：(a) 在 manifest 记录刷新前的原快照（第 2 步 `before`）作为基线对照；(b) 若需严格回滚到原 `checked_at`，由 operator 在授权下按运维手册对 SQLite 单行恢复（超出 HTTP 测试范围）；否则以"刷新后的快照"为新的合法状态。退出前确认 `/readyz` 7 tier、provider/deployment 列表未变、无未清空注入；不得因本 case 删除任何 provider/deployment/service-level。B 类整班结束由 fixture `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)(../llmtier-system-test-scheme.md)：Run ID=`<date>/A-api`；保存原始 status/headers/body（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。**本 case 额外证据**：刷新请求/响应、刷新前/后 `GET .../usage`（含 `checked_at`，证明持久化）。

- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；`admin_client` fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）；既存 provider `provider_local`（local 类型）；`ProviderAccountUsageSnapshot` 机器契约；实现 `src/management/account_usage.py`；自动化入口 [`at_adm_prov_usage_03.py`](../../../../tests/system/api_test_v03/at_adm_prov_usage_03.py)。**不依赖**其它 Case；与 ST-pusage-002（缺确认拒绝）互补，各自独立执行。

> 实现状态：Implemented（[`at_adm_prov_usage_03.py`](../../../../tests/system/api_test_v03/at_adm_prov_usage_03.py)）；执行状态与 Verdict 只在 Run 报告。
