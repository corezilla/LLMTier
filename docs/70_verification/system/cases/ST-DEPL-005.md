<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-DEPL-005 — 删除 deployment

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-DEPL-005` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-DEPL-005.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-DEPL-005`）；责任摘要、分类与优先级以 [系统测试方案 §3](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 Deployment CRUD 接口（/v1/deployments）（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-001`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-DEPL-005` 可追到方案清单行与 Run 报告。

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-DEPL-005` / 系统设计 §8 Deployment CRUD 接口（/v1/deployments） / `VRC-MGMT-001` / `normal` / `P0`
- **测试方法（§1.5 方法表行）**：等价类划分 + 契约字段比对
- 方案清单登记：`ST-DEPL-005`（与 §3.2 权威清单一致；本文件名 `st-depl-005.md`，唯一对应）。
- 要测什么（责任展开）：`DELETE /v1/deployments/{id}` 携带正确 `If-Match` 删除 deployment：HTTP 204，随后 `GET` 返回 404。
- 明确不测什么 / 失败含义：不证明 缺 `If-Match` 的 412（ST-PROV-009 同机制；本 case 走正确 ETag 路径）、不证明被引用删除的 409 `resource_in_use`（基线 `depl_b` 被 7 tier 引用；本 case **不**删它）、不证明列表/详情（ST-DEPL-001/03）、不证明更新（ST-DEPL-004）；本 case 只删本次自建 deployment，不触上游。

**目的（被测契约）**：验证 Management Deployment CRUD 的**删除契约**。被测端点/规则：`DELETE /v1/deployments/{deployment_id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `deleteDeployment`，`security=AdminBearerAuth`），`If-Match` 必须等于当前 ETag `"<id>.v<N>"`；成功 `204` 无 body（[`registry.delete_deployment`](../../../../src/management/registry.py)）；失败 404 `not_found` / 409 `resource_in_use`（被 service level 引用）/ 412 `version_conflict`（缺/过期 If-Match）。设计验证项 `VRC-MGMT-001`；需求/机制链 `LT-FUN-005`、`LT-INT-008`、`R-CFG-01`、`T-CFG-CAS`、`CT-ADMIN-001`（[系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）。**不证明什么**：不证明缺 `If-Match` 的 412（ST-PROV-009 同机制；本 case 走正确 ETag 路径）、不证明被引用删除的 409 `resource_in_use`（基线 `depl_b` 被 7 tier 引用；本 case **不**删它）、不证明列表/详情（ST-DEPL-001/03）、不证明更新（ST-DEPL-004）；本 case 只删本次自建 deployment，不触上游。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)/§2.4）。执行前须满足[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go)(../llmtier-system-test-scheme.md) **附加（B 类）**：实例 `/healthz` 200；`_baseline_settings` 注入 1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier。fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）：`llmtier_b`、`admin_client_b`。初始状态：m5air 上级基线由 `_baseline_settings` 提供；`depl_b` probe `healthy`。**TS-003**：`prov_b.endpoint` 必须是 LAN IP 上的 fake provider，**禁止 `127.0.0.1` 作为被测服务的上游 endpoint**。

## 3. 输入构造

- **输入与构造**：先创建独立 deployment，再删除（避免删基线 `depl_b`——它被 7 tier 引用，删除会 409）：
  ```http
  POST /v1/deployments HTTP/1.1          # 创建：provider_id=prov_b, capabilities 12 键, enabled=true
  DELETE /v1/deployments/{rid} HTTP/1.1
  Authorization: Bearer dev-admin
  If-Match: "<rid>.v1"
  ```
  构造点：`If-Match` **取自创建响应（或先 `GET`）的 `ETag`**（绝不硬编码）；删除目标必须是**本 case 自建**、未被 service level 引用的 deployment；不注入故障。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `create = admin_client_b.post("/v1/deployments", json=<DeploymentWrite, provider_id="prov_b">)`；断言 `201`，记 `rid`、`etag = create.headers["ETag"]`。
  3. `del = admin_client_b.delete(f"/v1/deployments/{rid}", headers={"If-Match": etag})`。
  4. 断言 `del.status_code == 204`；断言响应体为空（204 无 body）。
  5. `get = admin_client_b.get(f"/v1/deployments/{rid}")`；断言 `404` 且 `error.code == "not_found"`（信封 5 键、`type=="request_error"`）。
  6. 交叉核对：`GET /v1/deployments`（或按 id 过滤）确认 `rid` 不再出现，且基线 `depl_b` 仍在。**注**：该列表 GET（[`admin.page()`](../../../../src/management/admin.py)）会在 M007 `query_snapshots`/`query_snapshot_items` 落一条 10 分钟 TTL 的分页快照（即使无 `cursor`），属服务端读路径副作用、非用户资源，报告须登记，**不得声称"零写入"**。

**重点关注步骤**：① **204 无 body**——不得把删除响应当 JSON 解析；② **If-Match 必需且正确**——用创建响应的真实 ETag；缺/过期属 412（ST-PROV-009 同机制，本 case 不重测）；③ **删除自己创建物**——**绝不**删基线 `depl_b`（被 7 tier 引用，会 409 `resource_in_use`），否则破坏 B 类基线并威胁整班；④ **二次核验 404**——删除后 `GET` 必须 404 且 `code=not_found`，证明真删；⑤ **不触上游**——删除只写注册表；⑥ **幂等语义**——重复 DELETE 同一 id 期望 404（本 case 只发一次，不重测幂等）；⑦ **列表读路径副作用**——第 6 步列表 GET 会在 `query_snapshots` 落一条 10 分钟 TTL 的分页快照（`admin.page()`），报告须登记，**不得声称"零写入"**。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `deleteDeployment` 204 + ETag/CAS 规则。
  - 创建：`201`，ETag `"<rid>.v1"`。
  - DELETE：`204`，无 body。
  - 随后 GET：`404`，`error.code=="not_found"`（恰 5 键、`type=="request_error"`）。
  - 基线 `depl_b` 仍在 `GET /v1/deployments` 中。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`DELETE` → `204`（无 body），随后 `GET` → `404 not_found`，且基线未被破坏。
  - **FAIL**：DELETE status 非 204、随后 GET 非 404、错误信封不符，或误删基线/引用资源。
  - **BLOCKED**：无法执行/无法判定且可重试——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：B 类临时实例/fixture 不可用——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：伪造 204/404、硬编码 ETag，或用 `127.0.0.1` 作上游 endpoint——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**teardown 即删除动作本身**——本 case 的 DELETE 已完成清理，无剩余创建物（若 DELETE 失败或中途异常，须在 `finally` 中重取最新 ETag 后重试删除，或记录并保留证据）。不改基线 `depl_b`/`prov_b`/7 tier、不写注入。第 6 步列表 GET 的 `query_snapshots` 分页快照（10 分钟 TTL）随 B 类整班 `rm -rf` 消失，无需手工删除。B 类整班结束由 fixture `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）。离开前确认本 case 创建物已删净、基线仍在。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)(../llmtier-system-test-scheme.md)：Run ID=`<date>/B-api`；保存请求与原始响应（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。**本 case 额外证据**：创建/DELETE/随后 GET 的请求与原始响应（含 `If-Match`）、删除前后 deployment 列表。

- **依赖**：B 类 fixture `llmtier_b`/`admin_client_b`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）；基线 provider `prov_b`；`DeploymentWrite`/`ErrorEnvelope` 机器契约；实现 `src/management/registry.py` `delete_deployment`；机制 `T-CFG-CAS`；自动化入口 [`at_adm_depl_05.py`](../../../../tests/system/api_test_v03/at_adm_depl_05.py)。**不依赖**其它 Case（自建被测 deployment）；与 ST-DEPL-002/04 共享创建前置但各自独立执行。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
