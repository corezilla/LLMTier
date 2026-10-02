<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-PROV-008 — 删除 provider

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-PROV-008` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-PROV-008.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-PROV-008`）；责任摘要、分类与优先级以 [系统测试方案 §3](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 Provider CRUD 接口（/v1/providers）（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-001`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-PROV-008` 可追到方案清单行与 Run 报告。

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-PROV-008` / 系统设计 §8 Provider CRUD 接口（/v1/providers） / `VRC-MGMT-001` / `normal` / `P0`
- **测试方法（§1.5 方法表行）**：等价类划分 + 契约字段比对
- 方案清单登记：`ST-PROV-008`（与 §3.2 权威清单一致；本文件名 `st-prov-008.md`，唯一对应）。
- 要测什么（责任展开）：`DELETE /v1/providers/{id}` 携带正确 `If-Match` 删除无引用 provider：HTTP 204，随后 `GET` 404。
- 明确不测什么 / 失败含义：不证明 缺/过期 `If-Match` 的 412（ST-PROV-009）、不证明被引用 409（ST-PROV-010）、不证明删除 deployment/service-level；本 case 删除**本 case 新建且无引用**的 provider。

**目的（被测契约）**：验证 Management Provider CRUD 的**删除契约**。被测端点/规则：`DELETE /v1/providers/{id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `deleteProvider`，`security=AdminBearerAuth`）；
`If-Match` 必须等于当前 ETag `"<id>.v<N>"`；被删除前须确认无 deployment 引用；成功 `204 No Content`（空 body）；失败 404 `not_found` / 409 `resource_in_use`（被引用，ST-PROV-010）/ 412 `version_conflict`（ST-PROV-009）。
设计验证项 `VRC-MGMT-001`；机制 `T-CFG-CAS`；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`CT-ADMIN-001`。**不证明什么**：不证明缺/过期 `If-Match` 的 412（ST-PROV-009）、不证明被引用 409（ST-PROV-010）、不证明删除 deployment/service-level；
本 case 删除**本 case 新建且无引用**的 provider。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)/§2.4）。执行前须满足[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go)(../llmtier-system-test-scheme.md) **附加（B 类）**：实例 `/healthz` 200；`_baseline_settings` 注入 1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier。fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）：`llmtier_b`、`admin_client_b`。初始状态：m5air 上级基线由 `_baseline_settings` 提供。**TS-003**：请求中的 `endpoint` 用 LAN 常量 `LAN_PROVIDER_ENDPOINT`（可用 `LLMTIER_TEST_PROVIDER_URL` 覆盖），**禁止 `127.0.0.1`**。

## 3. 输入构造

- **输入与构造**：先创建无引用 provider，再 DELETE：
  ```http
  POST /v1/providers HTTP/1.1   # kind=local, endpoint=LAN, secret_ref=null, enabled=true
  DELETE /v1/providers/{rid} HTTP/1.1
  Authorization: Bearer dev-admin
  If-Match: "<rid>.v1"
  ```
  构造点：`rid`/`ETag` 取自创建响应（**绝不硬编码版本**）；新建 provider 无 deployment 引用，删除必然可成功。不注入故障；不构造非法输入。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `create = admin_client_b.post("/v1/providers", json={…})`；断言 `201`，记 `rid`、`etag = headers["ETag"]`。
  3. `del_resp = admin_client_b.delete(f"/v1/providers/{rid}", headers={"If-Match": etag})`；断言 `status_code == 204` 且响应 body 为空。
  4. `get_resp = admin_client_b.get(f"/v1/providers/{rid}")`；断言 `status_code == 404`、`error.code == "not_found"`。
  5. 可选：`GET /v1/providers` 列表确认 `rid` 不再出现。**注**：该列表 GET（[`admin.page()`](../../../../src/management/admin.py)）会在 M007 `query_snapshots`/`query_snapshot_items` 落一条 10 分钟 TTL 的分页快照（即使无 `cursor`），属服务端读路径副作用、非用户资源，报告须登记，**不得笼统声称"零写入"**。
  6. （teardown）**无**——本 case 已在步骤 3 删除创建物；若步骤 3 未成功，则 `finally` 内以 `GET` 的 ETag 重试 `DELETE`。

**重点关注步骤**：① **204 空 body**——删除成功为 `204 No Content`，不得返回 200 带 body；② **删除后不可见**——随后 `GET` 必须 404 `not_found`（软删/残留即 FAIL）；
③ **If-Match 正确**——用创建响应的 ETag；若 412，先 `GET` 取新 ETag 再删；④ **不误删基线**——只删本 case 创建的 provider，绝不碰 `prov_b`；⑤ **幂等性边界**——第二次 DELETE 同 id 应为 404；
⑥ **零残留**——teardown 后该 id 在列表/详情均不可见；⑦ **列表读路径副作用**——第 5 步可选列表 GET 会在 `query_snapshots` 落一条 10 分钟 TTL 的分页快照（`admin.page()`），报告须登记，**不得声称"零写入"**。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `deleteProvider` 204 + ETag 规则。
  - DELETE：`204`，无 body。
  - 随后 GET：`404` + `error.code=="not_found"`。
  - 列表：不含该 `rid`。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`204` 且 body 空；随后 `GET 404 not_found`；列表不含该 id。
  - **FAIL**：status 非 204、删除后仍可读（残留）、或误删其它资源。
  - **BLOCKED**：无法执行/无法判定且可重试——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：B 类临时实例/fixture 不可用——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：以替代路径/伪造 204 冒充——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**teardown 由本 case 的 DELETE 承担**；若删除失败，`finally` 内重试（必要时先取新 ETag）。不改 `prov_b`/`depl_b`、不写注入。第 5 步可选列表 GET 的 `query_snapshots` 分页快照（10 分钟 TTL）由服务端自身产生，B 类整班 `rm -rf` 临时目录时随库消失，无需手工删除。B 类整班结束由 fixture `stop()` + `rm -rf` 销毁（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)(../llmtier-system-test-scheme.md)：Run ID=`<date>/B-api`；保存请求与原始响应（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。**本 case 额外证据**：创建/DELETE/回读/列表的请求与原始响应。

- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）；`deleteProvider` 机器契约；CAS/ETag 规则 `registry.delete_provider`/`_etag`；机制 `T-CFG-CAS`；自动化入口 [`ST-PROV-008.py`](../../../../tests/system/cases/ST-PROV-008.py)。**不依赖**其它 Case；与 ST-PROV-009（缺 If-Match 412）、ST-PROV-010（被引用 409）互补但各自独立。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
