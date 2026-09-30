<!-- STD_DOCUMENT_COVER_BEGIN -->
# ADM-PROV-11 — kind 枚举校验

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ADM-PROV-11` |
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
| Canonical Path | `docs/70_verification/specifications/cases/adm-prov-11.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ADM-PROV-11`）；责任摘要、分类与优先级以 [系统测试方案 §3](../../schemes/llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 Provider CRUD 接口（/v1/providers）（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-001`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ADM-PROV-11` 可追到方案清单行与 Run 报告。

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ADM-PROV-11` / 系统设计 §8 Provider CRUD 接口（/v1/providers） / `VRC-MGMT-001` / `negative` / `P1`
- 方案清单登记：`ADM-PROV-11`（与 §3.2 权威清单一致；本文件名 `adm-prov-11.md`，唯一对应）。
- 要测什么（责任展开）：`POST /v1/providers` 提交非法 `kind`：HTTP 400 + `error.code=="invalid_request"`（`param=="kind"`），不创建资源。
- 明确不测什么 / 失败含义：不证明 成功创建（ADM-PROV-02）、不证明 `secret_ref` 格式（ADM-PROV-12）、不证明 `name`/`enabled`/`usage` 校验；本 case 只锁定单一非法 `kind`。

**目的（被测契约）**：验证 Management Provider CRUD 的**枚举校验（写前置校验）契约**。被测端点/规则：`POST /v1/providers`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `createProvider`，`ProviderWrite.kind` enum `{cloud,local}`）；[`registry.create_provider`](../../../../src/management/registry.py) `require(body["kind"] in {"cloud","local"}, 400, "invalid_request", "Invalid provider kind", "kind")`；失败走统一错误信封 `{error:{message,type,code,param,retryable}}`（400 `invalid_request`、`param=="kind"`）。设计验证项 `VRC-MGMT-001`；错误目录 `ERR-REQ-VALIDATION`（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`CT-ADMIN-001`。**不证明什么**：不证明成功创建（ADM-PROV-02）、不证明 `secret_ref` 格式（ADM-PROV-12）、不证明 `name`/`enabled`/`usage` 校验；本 case 只锁定单一非法 `kind`。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)/§2.4）。执行前须满足[系统测试计划 §3 执行前检](../../plans/llmtier-system-test-plan.md#3-执行前检go--no-go)(../../schemes/llmtier-system-test-scheme.md) **附加（B 类）**：实例 `/healthz` 200；`_baseline_settings` 注入 1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier。fixture（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）：`llmtier_b`、`admin_client_b`。初始状态：m5air 上级基线由 `_baseline_settings` 提供。**TS-003**：请求中的 `endpoint` 仍用 LAN 常量，即便本 case 期望被拒，也不得写 `127.0.0.1`。

## 3. 输入构造

- **输入与构造**：固定请求（`kind` 取枚举外值）：
  ```http
  POST /v1/providers HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-admin
  Content-Type: application/json
  ```
  ```json
  {
    "name": "Test Provider <uuid8>",
    "kind": "invalid_kind",
    "endpoint": "http://192.168.1.9:9000/v1",
    "secret_ref": null,
    "enabled": true
  }
  ```
  构造点：`kind="invalid_kind"`（不在 `{cloud,local}`）；其余字段均合法，确保 400 由 `kind` 触发而非别的字段；`name` 唯一。不注入故障。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. 记 `before = {p["id"] for p in admin_client_b.get("/v1/providers").json()["data"]}`（可选基线）。
  3. `resp = admin_client_b.post("/v1/providers", json=body_illegal_kind)`；断言 `status_code == 400`。
  4. `err = resp.json()["error"]`：`err["code"] == "invalid_request"`、`err["type"] == "request_error"`、`err["retryable"] is False`；若断言严格，`err["param"] == "kind"`。
  5. 交叉核对：`GET /v1/providers` 列表与步骤 2 记的集合一致（**对 provider 资源拒绝零副作用**，无新 provider）。**注**：第 2/5 步列表 GET 各自会在 M007 `query_snapshots`/`query_snapshot_items` 落一条 10 分钟 TTL 的分页快照（`admin.page()`，即使无 `cursor`），属服务端读路径副作用、非用户资源，报告须登记，**不得笼统声称"零写入"**。

**重点关注步骤**：① **400 而非 201**——非法枚举必须在写库前被拒；② **`param=="kind"`**——定位到出错字段（实现显式设置 `param="kind"`），便于调用方修复；③ **信封 identity**——恰 5 键、`type=="request_error"`（400<500）、`retryable=false`、`param` 为字符串；④ **对 provider 资源零副作用**——第 5 步确认无新 provider、无 audit 成功记录、无 usage profile 孤儿行；但第 2/5 步列表 GET 会在 `query_snapshots` 落 10 分钟 TTL 分页快照（`admin.page()`），须登记该写入、**不得声称"零写入"**；⑤ **与 `resource_conflict` 区分**——本 case 是 400 校验错，不是重名 409；⑥ **不依赖 message 文案**。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ProviderWrite.kind` enum + `ErrorEnvelope`/`ErrorDetail` + `ERR-REQ-VALIDATION`。
  - HTTP：`400`；`Content-Type: application/json`。
   - body：`{"error":{"code":"invalid_request","type":"request_error","param":"kind","retryable":false,"message":"<nonempty>"}}`。
   - 无 provider 资源变化：provider 集合与请求前一致（第 2/5 步列表 GET 自身的 `query_snapshots` 分页快照写入不计为资源变化）。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==400` 且 `error.code=="invalid_request"`（且 `param=="kind"`）、`type=="request_error"`、`retryable is False`，provider 集合无新增（`query_snapshots` 分页快照写入不算副作用）。
  - **FAIL**：status 非 400（如 201 误建）、`code` 不符、缺/多键、`type` 错，或出现 provider 资源副作用。
  - **BLOCKED**：无法执行/无法判定且可重试——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：B 类临时实例/fixture 不可用——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：以替代路径/伪造 400 冒充——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——写入被拒，无创建物；不改 `prov_b`/`depl_b`、不写注入。第 2/5 步列表 GET 的 `query_snapshots` 分页快照（10 分钟 TTL）随 B 类整班 `rm -rf` 消失。B 类整班结束由 fixture `stop()` + `rm -rf` 销毁（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[系统测试计划 §6 证据与 Run 记录规则](../../plans/llmtier-system-test-plan.md#6-证据与-run-记录规则)(../../schemes/llmtier-system-test-scheme.md)：Run ID=`<date>/B-api`；保存请求与原始响应（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。**本 case 额外证据**：请求与 400 原始响应、请求前后 provider 列表。

- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b`（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）；`ProviderWrite`/`ErrorEnvelope` 机器契约；`registry.create_provider` 枚举校验；错误目录 `ERR-REQ-VALIDATION`；自动化入口 [`at_adm_prov_11.py`](../../../../tests/system/api_test_v03/at_adm_prov_11.py)。**不依赖**其它 Case；与 ADM-PROV-12 同属写校验负向但各自独立。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
