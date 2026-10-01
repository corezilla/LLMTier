<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-PROV-010 — 删除被引用 provider

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-PROV-010` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-PROV-010.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-PROV-010`）；责任摘要、分类与优先级以 [系统测试方案 §3](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 Provider CRUD 接口（/v1/providers）（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-001`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-PROV-010` 可追到方案清单行与 Run 报告。

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-PROV-010` / 系统设计 §8 Provider CRUD 接口（/v1/providers） / `VRC-MGMT-001` / `negative` / `P1`
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（ERR-*）
- 方案清单登记：`ST-PROV-010`（与 §3.2 权威清单一致；本文件名 `st-prov-010.md`，唯一对应）。
- 要测什么（责任展开）：`DELETE /v1/providers/{id}` 删除被活动 deployment 引用的 provider：HTTP 409 + `error.code=="resource_in_use"`，provider 保留。
- 明确不测什么 / 失败含义：不证明 成功删除（ST-PROV-008）、不证明缺/过期 If-Match 412（ST-PROV-009）、不证明 deployment 侧删除被 service-level 引用的 409；本 case 依赖 baseline `prov_b → depl_b` 的引用关系，不删除任何资源（删除必然被拒）。
  > 规范注记：§3.2 行与 §11.1 均记本 case 错误码为 `resource_in_use`（`ERR-INUSE`）；实现与 [`at_adm_prov_10.py`](../../../../tests/system/api_test_v03/at_adm_prov_10.py) 一致。若外部简报把它写作 `resource_conflict`，以 `openapi` enum + 源码为准（`resource_conflict` 是**重名/已存在**语义，见 ST-PROV-002 重名分支，非引用保护）。

**目的（被测契约）**：验证 Management Provider CRUD 的**引用完整性（删除引用保护）契约**。被测端点/规则：`DELETE /v1/providers/{id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `deleteProvider`，`security=AdminBearerAuth`）；当该 provider 被任一 deployment 引用时，[`registry.delete_provider`](../../../../src/management/registry.py) 抛 `ApiError(409, "resource_in_use", "Provider is referenced by a deployment")`；前提是 `If-Match` 已匹配（否则先 412）。设计验证项 `VRC-MGMT-001`；错误目录 `ERR-INUSE` → `resource_in_use`；机制 `T-CFG-DELREF`；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`CT-ADMIN-001`。**不证明什么**：不证明成功删除（ST-PROV-008）、不证明缺/过期 If-Match 412（ST-PROV-009）、不证明 deployment 侧删除被 service-level 引用的 409；本 case 依赖 baseline `prov_b → depl_b` 的引用关系，不删除任何资源（删除必然被拒）。
  > 规范注记：§3.2 行与 §11.1 均记本 case 错误码为 `resource_in_use`（`ERR-INUSE`）；实现与 [`at_adm_prov_10.py`](../../../../tests/system/api_test_v03/at_adm_prov_10.py) 一致。若外部简报把它写作 `resource_conflict`，以 `openapi` enum + 源码为准（`resource_conflict` 是**重名/已存在**语义，见 ST-PROV-002 重名分支，非引用保护）。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)/§2.4）。执行前须满足[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go)(../llmtier-system-test-scheme.md) **附加（B 类）**：实例 `/healthz` 200；`_baseline_settings` 注入 1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier。fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）：`llmtier_b`、`admin_client_b`。初始状态：1 provider（`prov_b`）/ 1 deployment（`depl_b`）/ 7 fixed tier。`depl_b.provider_id == "prov_b"`、7 tier 的 `deployment_ids` 均指向 `depl_b`；`_probe_deployment(depl_b)` 断言 `healthy`。**本 case 不新建资源，直接对 baseline `prov_b` 发删除**（预期被拒，故不破坏基线）。

## 3. 输入构造

- **输入与构造**：固定两步（先取真实 ETag，再删除）：
  ```http
  GET /v1/providers/prov_b HTTP/1.1
  Authorization: Bearer dev-admin

  DELETE /v1/providers/prov_b HTTP/1.1
  Authorization: Bearer dev-admin
  If-Match: "<GET 返回的 ETag，形如 prov_b.v1>"
  ```
  构造点：`prov_b` 被 `depl_b` 引用（baseline 固定）；`If-Match` **取自 `GET` 的响应头**（绝不硬编码，version 会随前序 B 类写 case 变化）；本 case 不附带 body。不注入故障；不构造非法输入（缺/错 If-Match 会先得 412，属 ST-PROV-009，不是本 case 的目标码）。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `current = admin_client_b.get("/v1/providers/prov_b")`；断言 `200`，记 `etag = current.headers.get("ETag")`（必须存在）。
  3. `del_resp = admin_client_b.delete("/v1/providers/prov_b", headers={"If-Match": etag})`。
  4. 断言 `del_resp.status_code == 409`；`err = del_resp.json()["error"]`：`err["code"] == "resource_in_use"`、`err["type"] == "request_error"`、`err["retryable"] is False`；`"referenced" in err["message"].lower()`。
  5. 交叉核对：`GET /v1/providers/prov_b` 仍 `200`、`version`/ETag 未变（资源保留）。
  6. （teardown）**无 teardown**——删除被拒，基线未被触碰；不删除 `prov_b`/`depl_b`。

**重点关注步骤**：① **409 而非 412/404**——`If-Match` 正确后必须先过 CAS，再因引用被拒 409；若得 412，说明 ETag 取错（版本已变）；② **码必须是 `resource_in_use`**——引用保护语义，不是 `resource_conflict`（重名）也不是 `version_conflict`（CAS）；③ **资源保留**——第 5 步确认 `prov_b` 与引用关系未变；④ **不得真删基线**——本 case 绝不能在拒绝前删除 `prov_b`（否则破坏整个 B 类 session）；⑤ **ETag 必须实取**——B 类前序写 case 会推进 `prov_b` 版本（如 ST-PROV-013 usage），硬编码会 412。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ErrorEnvelope`/`ErrorDetail` + `ERR-INUSE` 语义（不依赖 message 文案）。
  - GET：`200` + ETag。
  - DELETE：`409`；body `error.code=="resource_in_use"`、`type=="request_error"`、`retryable is False`、`message` 含 `referenced`（语义旁证）。
  - 资源保留：`GET` 仍 `200`，版本未推进。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`DELETE 409` + `error.code=="resource_in_use"`；`GET` 仍 `200` 且版本不变。
  - **FAIL**：status 非 409（如 204 误删/412）、`code` 不符（如 `resource_conflict`/`version_conflict`）、或基线被破坏。
  - **BLOCKED**：无法执行/无法判定且可重试（fixture 缺 `prov_b`/`depl_b` 引用、断言逻辑问题）——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：B 类临时实例/fixture 不可用，或 `prov_b`/`depl_b` 基线未建立——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：伪造 409、或真正删除基线后以 mock 冒充——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——删除被拒，`prov_b`/`depl_b` 与 7 tier 均未变；不写注入。B 类整班结束由 fixture `stop()` + `rm -rf` 销毁（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）。离开前确认 `prov_b` 仍在、`/readyz` 7 tier。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)(../llmtier-system-test-scheme.md)：Run ID=`<date>/B-api`；保存请求与原始响应（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。**本 case 额外证据**：`GET prov_b`（含 ETag）、`DELETE` 请求与 409 原始响应、拒绝后回读、`GET /v1/deployments/depl_b` 引用快照。

- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b` 与 baseline `prov_b`+`depl_b`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）；`deleteProvider`/`ErrorEnvelope` 机器契约；`registry.delete_provider` 引用检查；机制 `T-CFG-DELREF`；错误目录 `ERR-INUSE`；自动化入口 [`at_adm_prov_10.py`](../../../../tests/system/api_test_v03/at_adm_prov_10.py)。**不依赖**其它 Case（依赖 baseline 引用关系，而非某 case 先跑）；与 ST-PROV-008/09 互补但各自独立。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
