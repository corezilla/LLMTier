<!-- STD_DOCUMENT_COVER_BEGIN -->
# ADM-PROV-07 — 过期 ETag

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ADM-PROV-07` |
| Document Version | `0.1.0-draft.1` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-29` |
| Last Modified Date | `2026-09-29` |
| Template ID | `tests.system-test-design` |
| Template Version | `2.3.0` |
| Template Conformance | `native` |
| Tailoring Reference | none |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/specifications/cases/adm-prov-07.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ADM-PROV-07` / 系统设计 §8 Provider CRUD 接口（/v1/providers） / `VRC-MGMT-002` / `concurrency` / `P1`
- 方案清单登记：`ADM-PROV-07`（与 §3.2 权威清单一致；本文件名 `adm-prov-07.md`，唯一对应）。
- 要测什么（责任展开）：`PATCH /v1/providers/{id}` 携带**过期/错误** `If-Match`：HTTP 412 + `error.code=="version_conflict"` + `error.current_version`，无写入。
- 明确不测什么 / 失败含义：不证明 成功更新（ADM-PROV-05）、不证明**缺头** 412（ADM-PROV-06）、不证明 DELETE 的过期 ETag（本 case 只发 PATCH）、不证明并发两写者（§5）；本 case 只锁定"头存在但值过期"。

**目的（被测契约）**：验证 Management Provider CRUD 的**乐观并发前置校验（过期前置条件）**。被测端点/规则：`PATCH /v1/providers/{id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `updateProvider`，`security=AdminBearerAuth`）；当 `If-Match` 形态合法但**不等于**当前 ETag 时，[`registry.update_provider`](../../../../src/management/registry.py) 抛 `ApiError(412, "version_conflict", extra={"current_version": <N>})`；wire 信封含额外键 `current_version`。设计验证项 `VRC-MGMT-002`；错误目录 `ERR-STALE` → `version_conflict`；机制 `T-CFG-CAS`；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`CT-ADMIN-001`。**不证明什么**：不证明成功更新（ADM-PROV-05）、不证明**缺头** 412（ADM-PROV-06）、不证明 DELETE 的过期 ETag（本 case 只发 PATCH）、不证明并发两写者（§5）；本 case 只锁定"头存在但值过期"。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)/§2.4）。执行前须满足[系统测试计划 §3 执行前检](../../plans/llmtier-system-test-plan.md#3-执行前检go--no-go)(../../schemes/llmtier-system-test-scheme.md) **附加（B 类）**：实例 `/healthz` 200；`_baseline_settings` 注入 1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier。fixture（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）：`llmtier_b`、`admin_client_b`。初始状态：m5air 上级基线由 `_baseline_settings` 提供；`depl_b` probe `healthy`。**TS-003**：请求中的 `endpoint` 用 LAN 常量 `LAN_PROVIDER_ENDPOINT`（可用 `LLMTIER_TEST_PROVIDER_URL` 覆盖），**禁止 `127.0.0.1`**。

## 3. 输入构造

- **输入与构造**：先创建独立 provider，再发带**错误** `If-Match` 的 PATCH：
  ```http
  POST /v1/providers HTTP/1.1   # kind=local, endpoint=LAN, secret_ref=null, enabled=true
  PATCH /v1/providers/{rid} HTTP/1.1
  Authorization: Bearer dev-admin
  If-Match: "<rid>.v99"
  Content-Type: application/json
  ```
  ```json
  {"name": "Stale Update"}
  ```
  构造点：`rid` 取自创建响应；`If-Match` 构造为 `"<rid>.v99"`——**形态合法**（`"<id>.v<N>"` 含双引号）但版本值远超当前（过期/不存在），确保 412 由**值不匹配**触发而非格式错；body 仅含合法字段。不注入故障。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `create = admin_client_b.post("/v1/providers", json={…})`；断言 `201`，记 `rid`、`version_before`、`name_before`。
  3. `bad_etag = '"' + rid + '.v99"'`；`patch = admin_client_b.patch(f"/v1/providers/{rid}", json={"name":"Stale Update"}, headers={"If-Match": bad_etag})`。
  4. 断言 `patch.status_code == 412`；`err = patch.json()["error"]`：`err["code"] == "version_conflict"`、`err["type"] == "request_error"`、`err["retryable"] is False`、`err["current_version"] == version_before`（≠ 99）。
  5. 交叉核对：`GET` 断言 `name==name_before`、`version==version_before`、ETag 未变（零副作用）。
  6. （teardown，`finally` 内）以当前 ETag `DELETE`，断言 `204`；`GET` 断言 `404`。

**重点关注步骤**：① **形态合法但值错**——`"<rid>.v99"` 是刻意构造的过期 ETag；若实现把格式错也当 412 会掩盖真实问题，故 body 保持合法、只让版本值错；② **`current_version` 揭示真实版本**——断言它等于创建后的版本（证明实现知道当前值），而非回显请求值；③ **零副作用**——拒绝不得推进 `version`/改 `name`；④ **与 ADM-PROV-06 的区分**——06 缺头（`None`），07 值不等；⑤ **teardown** 用当前版本删除。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ErrorEnvelope`/`ErrorDetail` + `ERR-STALE` + ETag 严格匹配规则。
  - HTTP：`412`；`Content-Type: application/json`。
  - body：`{"error":{"code":"version_conflict","type":"request_error","param":null,"retryable":false,"current_version":<version_before>, "message":"<nonempty>"}}`。
  - 无资源变化。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==412` 且 `error.code=="version_conflict"` 且 `error.current_version==version_before`、`type=="request_error"`、`retryable is False`；回读无变化；teardown 成功。
  - **FAIL**：status 非 412（含成功写入）、`code` 不符、`current_version` 缺失或错误、或出现副作用。
  - **BLOCKED**：无法执行/无法判定且可重试——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：B 类临时实例/fixture 不可用——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：伪造 412 或绕过真实 CAS——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**必须 teardown（`finally` 强制）**——删除本 case 创建的 provider；不改 `prov_b`/`depl_b`、不写注入。B 类整班结束由 fixture `stop()` + `rm -rf` 销毁（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[系统测试计划 §6 证据与 Run 记录规则](../../plans/llmtier-system-test-plan.md#6-证据与-run-记录规则)(../../schemes/llmtier-system-test-scheme.md)：Run ID=`<date>/B-api`；保存请求与原始响应（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。**本 case 额外证据**：创建/PATCH（含过期 `If-Match` 字面值）/回读/teardown 的请求与响应、`current_version`。

- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b`（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）；`ErrorEnvelope` 机器契约；CAS/ETag 规则 `registry.update_provider`/`_etag`；机制 `T-CFG-CAS`；错误目录 `ERR-STALE`；自动化入口 [`at_adm_prov_07.py`](../../../../tests/system/api_test_v03/at_adm_prov_07.py)。**不依赖**其它 Case；与 ADM-PROV-05/06 互补但各自独立。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
