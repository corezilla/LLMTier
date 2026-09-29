<!-- STD_DOCUMENT_COVER_BEGIN -->
# ADM-SL-05 — 删除 fixed tier

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ADM-SL-05` |
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
| Canonical Path | `docs/70_verification/specifications/cases/adm-sl-05.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ADM-SL-05` / 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） / `VRC-MGMT-002` / `negative` / `P0`
- 方案清单登记：`ADM-SL-05`（与 §3.2 权威清单一致；本文件名 `adm-sl-05.md`，唯一对应）。
- 要测什么（责任展开）：`DELETE /v1/service-levels/{id}` 删除固定 Tier：HTTP 409 `fixed_service_level`（"cannot be deleted"）。
- 明确不测什么 / 失败含义：不证明 `If-Match` 的 412（本实现对该路由先返回 409、不校验 ETag）、不证明其它资源删除（provider/deployment 引用 409 见 ADM-PROV-10）、不证明 PATCH/创建（ADM-SL-04/02/02b）。本 case **只**锁 409 `fixed_service_level`。

**目的（被测契约）**：验证固定 Tier 的**不可删除契约**。被测端点/规则：`DELETE /v1/service-levels/{service_level_id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `deleteServiceLevel`，header `If-Match`）；[`registry.delete_service_level`](../../../../src/management/registry.py) **无条件** `raise ApiError(409, "fixed_service_level", "Fixed Tier service levels cannot be deleted")`（不存在可删除分支）。设计验证项 `VRC-MGMT-002`；错误目录 `ERR-FIXED-LEVEL` → wire `code=fixed_service_level`；机制 `T-CFG-DELREF` 的固定 Tier 特例；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`CT-ADMIN-001`。**不证明什么**：不证明 `If-Match` 的 412（本实现对该路由先返回 409、不校验 ETag）、不证明其它资源删除（provider/deployment 引用 409 见 ADM-PROV-10）、不证明 PATCH/创建（ADM-SL-04/02/02b）。本 case **只**锁 409 `fixed_service_level`。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 附加（B 类）；fixture `admin_client_b`（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；本 case 选 `Engineer`。

## 3. 输入构造

- **输入与构造**：
  ```http
  DELETE /v1/service-levels/Engineer HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-admin
  If-Match: "<从 GET 读取的真实 ETag>"
  ```
  构造点：先 `GET` 取真实 `ETag`（实现不校验，但按 openapi 契约提供，使失败点确为固定 Tier 规则）；不传 body；不注入故障。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `get = admin_client_b.get("/v1/service-levels/Engineer")`；断言 200；记 `etag = get.headers["ETag"]`、`version_before = body["version"]`。
  3. `resp = admin_client_b.delete("/v1/service-levels/Engineer", headers={"If-Match": etag})`。
  4. 断言 `resp.status_code == 409`；`err = resp.json()["error"]`：断言 `err["code"]=="fixed_service_level"`、`"cannot be deleted" in err["message"]`、`err["type"]=="request_error"`、`err["retryable"] is False`。
  5. （零副作用核验）`GET /v1/service-levels/Engineer` 仍 200，`version` 不变；`GET /v1/service-levels` 仍含全部 7 tier。

**重点关注步骤**：① **不可删除而非未找到**——必须是 409 `fixed_service_level`，不是 404/400/412；② **零副作用**——`Engineer` 行与其 `service_level_deployments` 必须保留（409 抛在 `txn` 内、回滚）；③ **ETag 不参与判定**——本实现删除前不校验 `If-Match`（`delete_service_level` 直接抛 409），因此传任意/缺省 `If-Match` 也应 409；不得因"实现忽略了 ETag"而判 FAIL（这属实现注记，见下）；④ **错误信封 identity**——恰 5 键、`type=request_error`；⑤ **审计**——失败经 `mutate` 记 `action="service_level.delete"`、`result="failed"`。
  > **实现注记**：`delete_service_level` 对所有 `service-levels/{id}` 删除都返回 409 `fixed_service_level`（当前系统只存在固定 Tier，无自定义 Tier 删除路径）。OpenAPI 声明 DELETE 需 `If-Match`/可 412，但实现不校验 ETag —— 与本 case 的 409 断言一致；若未来引入可变 Tier，本 case 需按新契约复核。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ErrorEnvelope`/`ErrorDetail` + 固定 Tier 不可删除规则（[系统设计 §7.8](../../../20_system_design/llmtier-system-design.md)）。
  - HTTP：`409`；body `{"error":{"message":"Fixed Tier service levels cannot be deleted","type":"request_error","code":"fixed_service_level","param":null,"retryable":false}}`。
  - 资源：`Engineer` 仍存在，`version` 不变，7 tier 齐全。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`409` + `code=="fixed_service_level"` + `type=="request_error"`，且 `Engineer` 未被删除。
  - **FAIL**：status 非 409（含 204 删除成功）、`code` 错、或 `Engineer` 被删。
  - **BLOCKED**：fixture/断言逻辑问题——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：B 类临时实例不可用——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充，或未命中真实固定 Tier 规则——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——删除被拒未改库。退出前确认 7 tier 齐全、`Engineer.version` 未变、无注入残留。 B 类整班结束由 fixture `stop()` + `rm -rf` 临时目录（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存GET/DELETE 请求与原始 409 响应（脱敏后）、DELETE 后 `GET` 的 `version`、发出命令、exit code、`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../../plans/llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/B-api`，`environment:"b"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b`（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）；`registry.delete_service_level`；错误目录 `ERR-FIXED-LEVEL`。自动化入口 [`at_adm_sl_05.py`](../../../../tests/system/api_test_v03/at_adm_sl_05.py)。**不依赖**其它 Case；与 ADM-SL-06/07 同走 PATCH 冲突语义但独立执行。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
