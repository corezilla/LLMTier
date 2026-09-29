<!-- STD_DOCUMENT_COVER_BEGIN -->
# ADM-PROV-04 — 不存在 provider

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ADM-PROV-04` |
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
| Canonical Path | `docs/70_verification/specifications/cases/adm-prov-04.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ADM-PROV-04` / 系统设计 §8 Provider CRUD 接口（/v1/providers） / `VRC-MGMT-001` / `negative` / `P0`
- 方案清单登记：`ADM-PROV-04`（与 §3.2 权威清单一致；本文件名 `adm-prov-04.md`，唯一对应）。
- 要测什么（责任展开）：`GET /v1/providers/{id}` 读取不存在 provider：HTTP 404 + `error.code=="not_found"`，统一错误信封，无副作用。
- 明确不测什么 / 失败含义：不证明 存在（ADM-PROV-03）、不证明 update/delete 的 404（更新/删除未知 id 同属 `not_found`，但本 case 只发 GET）、不证明 `/usage`、`/models` 子路径的 404（ADM-PROV-MODELS-02、ADM-PROV-USAGE-04）、不证明鉴权优先于存在性（AUTH-09）。

**目的（被测契约）**：验证 Management Provider CRUD 的**不存在负向契约**。被测端点/规则：`GET /v1/providers/{id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `getProvider`，`security=AdminBearerAuth`），认证角色 `admin`；未知 id 走统一错误信封 `{error:{message,type,code,param,retryable}}` 的 `404` + `code=not_found`（[`registry.get_provider`](../../../../src/management/registry.py) `raise ApiError(404,"not_found",…)`）；`type=request_error`（<500）、`param=null`、`retryable=false`。设计验证项 `VRC-MGMT-001`；错误目录 `ERR-NOTFOUND`（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`CT-ADMIN-001`。**不证明什么**：不证明存在（ADM-PROV-03）、不证明 update/delete 的 404（更新/删除未知 id 同属 `not_found`，但本 case 只发 GET）、不证明 `/usage`、`/models` 子路径的 404（ADM-PROV-MODELS-02、ADM-PROV-USAGE-04）、不证明鉴权优先于存在性（AUTH-09）。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例；角色 `admin`，只读；见[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）。执行前必须通过[系统测试计划 §3 执行前检](../../plans/llmtier-system-test-plan.md#3-执行前检go--no-go)(../../schemes/llmtier-system-test-scheme.md) 的 6 项就绪检查（详见 §2.1）；任一失败 → 整班 BLOCKED/SKIP，不得改用模拟路径。fixture（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）：`admin_client`。初始状态：m5air 现有 3 provider / 4 deployment / 7 tier。

## 3. 输入构造

- **输入与构造**：固定请求（无请求体）：
  ```http
  GET /v1/providers/provider_does_not_exist_xyz HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：`{id}` 取一个保证不存在的字面量 `provider_does_not_exist_xyz`；无 body；不注入故障；不构造其它非法输入。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（`pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = admin_client.get("/v1/providers/provider_does_not_exist_xyz")`；记录 status、headers、body。
  3. 断言 `resp.status_code == 404`。
  4. `err = resp.json()["error"]`：断言键集恰为 `{message,type,code,param,retryable}`；`err["code"] == "not_found"`、`err["type"] == "request_error"`、`err["param"] is None`、`err["retryable"] is False`。
  5. 交叉核对：再次 `GET /v1/providers`，确认 provider 集合未因本次请求变化（**provider 列表无新增/删除**；注意该列表 GET 自身会在 `query_snapshots` 落一条 10 分钟 TTL 的分页快照，见 `admin.page()`，此为服务端读路径副作用、非 provider 资源变化，不得据此判 FAIL）。

**重点关注步骤**：① **状态与 code 双断言**——必须同时 `404` 且 `code==not_found`，不能只看到 404 就通过（404 也可能来自路由不命中）；② **信封 identity**——恰 5 键，`type` 由状态导出（404<500 ⇒ `request_error`），无 `category` 键，`param=null`、`retryable=false`；③ **对 provider 资源零副作用**——校验/读取失败在 dispatch 前完成，不改任何资源；第 5 步确认 provider 集合不变；但 **第 5 步的列表 GET 会在 `query_snapshots` 落一条 10 分钟 TTL 的分页快照**（`admin.page()`），这是服务端实现行为、非用户资源，报告须登记该写入，**不得笼统声称"零写入"**；④ **错误源可解释**——不得把鉴权失败（401/403）或路由 404 混入本 case（凭据固定 admin 且路径存在）；⑤ **不依赖 message 文本**——Oracle 只约束 code/type/param/retryable，不对 `message` 语义断言。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ErrorEnvelope`/`ErrorDetail` + `ERR-NOTFOUND` 目录（不依赖实现文案）。
  - HTTP：`404`；`Content-Type: application/json`。
   - body：`{"error":{"code":"not_found","type":"request_error","param":null,"retryable":false, "message":"<nonempty>"}}`（恰 5 键）。
   - 无 provider 资源变化：provider 集合与请求前一致（列表 GET 自身的 `query_snapshots` 分页快照写入不计为资源变化）。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==404` 且 `error.code=="not_found"` 且信封 5 键、`type=="request_error"`、`param is None`、`retryable is False`，且 provider 集合无变化（`query_snapshots` 分页快照写入不算副作用）。
  - **FAIL**：status 非 404（如 200/500）、`code` 不符、信封缺/多键、`type` 错，或出现 provider 资源副作用。
  - **BLOCKED**：测试代码/契约本身问题——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用替代路径/伪造 404 冒充——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——负向读失败对 provider 资源无写副作用；第 5 步列表 GET 的 `query_snapshots` 分页快照（10 分钟 TTL）由服务端自身产生，等待过期即可，不手工删除。退出前确认 `/readyz` 仍 7 tier、无未清空注入项；若误跑于 B 类实例，则按[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md) 整班 `stop()` + `rm -rf`。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[系统测试计划 §6 证据与 Run 记录规则](../../plans/llmtier-system-test-plan.md#6-证据与-run-记录规则)(../../schemes/llmtier-system-test-scheme.md)：Run ID=`<date>/A-api`；保存原始 status/headers/body（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。**本 case 额外证据**：请求前后 provider 列表快照。

- **依赖**：[系统测试计划 §3 执行前检](../../plans/llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；`admin_client` fixture（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）；`ErrorEnvelope` 机器契约；自动化入口 [`at_adm_prov_04.py`](../../../../tests/system/api_test_v03/at_adm_prov_04.py)。**不依赖**其它 Case；与 ADM-PROV-03 成对但各自独立。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
