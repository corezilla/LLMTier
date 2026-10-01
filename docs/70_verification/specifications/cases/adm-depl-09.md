<!-- STD_DOCUMENT_COVER_BEGIN -->
# ADM-DEPL-09 — provider_id 不可变（PATCH 另一个既存 provider）

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ADM-DEPL-09` |
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
| Canonical Path | `docs/70_verification/specifications/cases/adm-depl-09.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ADM-DEPL-09`）；责任摘要、分类与优先级以 [系统测试方案 §3](../../schemes/llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 Deployment CRUD 接口（/v1/deployments）（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-002`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ADM-DEPL-09` 可追到方案清单行与 Run 报告。

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ADM-DEPL-09` / 系统设计 §8 Deployment CRUD 接口（/v1/deployments） / `VRC-MGMT-002` / `negative` / `P1`
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（ERR-*）
- 方案清单登记：`ADM-DEPL-09`（与 §3.2 权威清单一致；本文件名 `adm-depl-09.md`，唯一对应）。
- 要测什么（责任展开）：`PATCH /v1/deployments/{id}` 试图把 `provider_id` 改为**另一个已存在**的 provider：HTTP 400 + `error.code=="invalid_request"`、`param=="provider_id"`，统一错误信封，`provider_id`/`version`/ETag 不变。（用既存 provider 作目标值，确保唯一命中 immutability 分支而非"未知 provider"分支。）
- 明确不测什么 / 失败含义：不证明 正常更新（ADM-DEPL-04）、不证明缺/过期 `If-Match` 的 412（本 case 用正确 ETag）、不证明删除（ADM-DEPL-05）、不证明 provider CRUD（ADM-PROV-*）；本 case 为纯负向，**不得**改动 deployment。

**目的（被测契约）**：验证 Deployment **`provider_id` 变更的不可变契约**。被测端点/规则：`PATCH /v1/deployments/{deployment_id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `updateDeployment`，`security=AdminBearerAuth`），`If-Match` 必须等于当前 ETag `"<id>.v<N>"`；[`registry.update_deployment`](../../../../src/management/registry.py) 在 `If-Match` 校验通过后 `if "provider_id" in body and body["provider_id"] != row["provider_id"]: raise ApiError(400, "invalid_request", "Deployment provider_id cannot be changed", "provider_id")`（L266-267）——不论目标 provider 是否存在，改值一律被拒（仅同值 no-op 允许）。设计验证项 `VRC-MGMT-002`；错误目录 `ERR-REQ-VALIDATION`（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；需求/机制链 `LT-FUN-005`、`LT-INT-008`、`R-CFG-01`、`T-CFG-CAS`、`CT-ADMIN-001`。**不证明什么**：不证明正常更新（ADM-DEPL-04）、不证明缺/过期 `If-Match` 的 412（本 case 用正确 ETag）、不证明删除（ADM-DEPL-05）、不证明 provider CRUD（ADM-PROV-*）；本 case 为纯负向，**不得**改动 deployment。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)/§2.4）。执行前须满足[系统测试计划 §3 执行前检](../../plans/llmtier-system-test-plan.md#3-执行前检go--no-go)(../../schemes/llmtier-system-test-scheme.md) **附加（B 类）**：实例 `/healthz` 200；`_baseline_settings` 注入 1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier。fixture（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）：`llmtier_b`、`admin_client_b`。初始状态：m5air 上级基线由 `_baseline_settings` 提供；`depl_b` probe `healthy`。**被测对象**：基线 `depl_b`（provider_id 原值 `prov_b`），本 case 只 PATCH 一个非法 `provider_id`，不改动 baseline。

## 3. 输入构造

- **输入与构造**：先 `GET` 基线 deployment 取 `ETag`，再 PATCH 非法引用：
  ```http
  GET /v1/deployments/depl_b HTTP/1.1
  Authorization: Bearer dev-admin

  PATCH /v1/deployments/depl_b HTTP/1.1
  Authorization: Bearer dev-admin
  If-Match: "<depl_b>.v<N>"
  Content-Type: application/json
  ```
  ```json
  {"provider_id": "<prov_b2>"}
  ```
  构造点：先用 `POST /v1/providers` 创建一个**第二个既存 provider**（`prov_b2`），PATCH 的目标值取其 id——确保被拒的唯一原因是 immutability（若用不存在 provider，会同时命中"未知 provider"这一独立 400 分支，判别力不足）；`If-Match` **必须取自先前的 `GET /v1/deployments/depl_b`**（绝不硬编码；若用错误 ETag 会先得 412 而非 400，本 case 须避免）；PATCH 体只含 `provider_id`（键集 ⊆ 允许集且非空）；不注入故障；teardown 删除 `prov_b2`。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `other = POST /v1/providers`；断言 `201`，记 `prov_b2 = other.json()["id"]`（≠ `prov_b`）。
  3. `get = admin_client_b.get("/v1/deployments/depl_b")`；断言 `200`，记 `etag = get.headers["ETag"]`、`before = get.json()`（`provider_id`/`version`）。
  4. `resp = admin_client_b.patch("/v1/deployments/depl_b", json={"provider_id": prov_b2}, headers={"If-Match": etag})`；记录 status、body。
  5. 断言 `resp.status_code == 400`。
  6. `err = resp.json()["error"]`：键集恰 5 键；`err["code"] == "invalid_request"`、`err["type"] == "request_error"`、`err["param"] == "provider_id"`、`err["retryable"] is False`。
  7. 零副作用：`after = GET /v1/deployments/depl_b`；断言 `after.json()["provider_id"] == before["provider_id"]`（仍 `prov_b`）、`after.json()["version"] == before["version"]`（未 +1），且 `ETag` 与第 3 步一致。
  8. （teardown，`finally` 内）`GET /v1/providers/{prov_b2}` 取最新 ETag → `DELETE` → 断言 `204`。

**重点关注步骤**：① **先 GET 再 PATCH**——`If-Match` 必须真实有效，否则会先命中 412 而测不到本 case 的 400（`update_deployment` 的 `If-Match` 校验先于 provider 校验）；② **400 + code + param 三断言**——`param=="provider_id"` 定位字段，且**不是 404**；③ **拒绝零副作用**——校验在 `UPDATE` 之前，第 7 步证明 `provider_id`/`version`/ETag 均未变；④ **只改一个字段**——PATCH 体仅 `provider_id`，避免与 capabilities 重算路径混淆；⑤ **不依赖 message 文本**——只断言 code/type/param/retryable；⑥ **目标是既存 provider**——保证唯一命中 immutability 分支。
  > **契约与实现（已对齐）**：§3.2 `ADM-DEPL-09` 标题为"`provider_id` 不可 PATCH"，即 `provider_id` 为不可变字段。实际 [`registry.update_deployment`](../../../../src/management/registry.py) 在 `If-Match` 校验后**强制**该不变量：`if "provider_id" in body and body["provider_id"] != row["provider_id"]: raise ApiError(400, "invalid_request", "Deployment provider_id cannot be changed", "provider_id")`（L266-267）。把 `provider_id` 改为另一个**既存** provider 同样被拒（同一 immutability 分支），仅**同值** no-op 被允许；换成不存在 provider 也 400（本 case 覆盖该值）。故本 case 以**已存在**的另一 provider id 作 PATCH 值，唯一命中 immutability 分支，判别力真实；"不可变"语义已被实现。脚本同时断言 `error.param=="provider_id"`、5 键信封、`type`/`retryable` 与零副作用（`provider_id`/`version`/ETag 不变）。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `DeploymentPatch` provider 引用约束 + `ErrorEnvelope`/`ERR-REQ-VALIDATION`。
  - HTTP：`400`；`Content-Type: application/json`。
  - body：`{"error":{"code":"invalid_request","type":"request_error","param":"provider_id","retryable":false,"message":"<nonempty>"}}`（恰 5 键）。
  - 无资源变化：`provider_id` 仍 `prov_b`、`version`/`ETag` 不变。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`400` 且 `code=="invalid_request"`、`param=="provider_id"`、信封 5 键、`type=="request_error"`，且 `depl_b` 的 `provider_id`/`version`/ETag 未变。
  - **FAIL**：status 非 400（如 200 成功改 provider_id、404、412）、code/param 不符、信封缺/多键，或 baseline 被改动。
  - **BLOCKED**：无法执行/无法判定且可重试——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：B 类临时实例/fixture 不可用——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：硬编码/伪造 `If-Match`（绕过真实 GET），或伪造 400——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——负向拒绝无写副作用，基线 `depl_b` 保持原值。退出前确认 `depl_b` 的 `provider_id=="prov_b"`、`version`/ETag 与执行前一致、7 tier 仍在、无未清空注入。B 类整班结束由 fixture `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[系统测试计划 §6 证据与 Run 记录规则](../../plans/llmtier-system-test-plan.md#6-证据与-run-记录规则)(../../schemes/llmtier-system-test-scheme.md)：Run ID=`<date>/B-api`；保存请求与原始响应（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。**本 case 额外证据**：`GET`（取 ETag）、PATCH 请求/原始响应、PATCH 后 `GET`（证明零副作用）。
  > **脚本覆盖（已对齐）**：现有 [`at_adm_depl_09.py`](../../../../tests/system/api_test_v03/at_adm_depl_09.py) 断言 `400` + `code=="invalid_request"` + `param=="provider_id"` + 5 键信封 + `type`/`retryable`，并回读证明 `provider_id`/`version`/ETag 未变；PATCH 目标为**另一个既存 provider**（本 case 自建并在 `finally` 删除），从而唯一命中 immutability 分支。

- **依赖**：B 类 fixture `llmtier_b`/`admin_client_b`（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）；基线 provider `prov_b` / deployment `depl_b`；`DeploymentPatch`/`ErrorEnvelope` 机器契约；ETag/CAS 规则 `registry.update_deployment`/`_etag`；机制 `T-CFG-CAS`；自动化入口 [`at_adm_depl_09.py`](../../../../tests/system/api_test_v03/at_adm_depl_09.py)。**不依赖**其它 Case；与 ADM-DEPL-04（正常 PATCH）互补但各自独立执行。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
