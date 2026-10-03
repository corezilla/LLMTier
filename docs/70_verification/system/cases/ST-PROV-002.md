<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-PROV-002 — 创建 provider

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-PROV-002` |
| Document Version | `0.1.0-draft.4` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-29` |
| Last Modified Date | `2026-10-03` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `native` |
| Tailoring Reference | none |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/cases/ST-PROV-002.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-PROV-002`）；责任摘要、分类与优先级以 [系统测试方案 §6](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 Provider CRUD 接口（/v1/providers）（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-001`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-PROV-002` 可追到方案清单行与 Run 报告。

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-PROV-002` / 系统设计 §8 Provider CRUD 接口（/v1/providers） / `VRC-MGMT-001` / `normal` / `P0`
- **测试方法（§2.2 方法表行）**：等价类划分 + 契约字段比对
- 方案清单登记：`ST-PROV-002`（与 计划 §3 权威清单一致；本文件名 `st-prov-002.md`，唯一对应）。
- 要测什么（责任展开）：`POST /v1/providers` 创建 provider：HTTP 201 + 自动 `id` + `has_secret`/`version` + `ETag` 响应头，且可经 `GET /v1/providers/{id}` 回读。
- 明确不测什么 / 失败含义：不证明 更新/删除/If-Match（ST-PROV-005..10）、不证明 `kind`/`secret_ref` 负向（ST-PROV-011/12）、不证明 `usage` 子对象更新（ST-PROV-013）、不证明重名 409（本 case 用随机名避开）、不证明响应不含 secret 的强断言（ST-PROV-014）；创建不触上游，故不证明 provider 可达性。

**目的（被测契约）**：验证 Management Provider CRUD 的**创建写契约**。被测端点/规则：`POST /v1/providers`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `createProvider`，`security=AdminBearerAuth`），请求体契约为 `ProviderWrite{name,kind,endpoint,secret_ref,enabled(,usage?)
}`；成功 `201 Created` + body `ProviderView` + 响应头 `ETag: "<id>.v<N>"`；`id` 由服务端自动生成（`_id("provider")` → `provider_<hex>`），`has_secret = (secret_ref is not None)`，初始 `version=1`；
失败走统一错误信封（400 `invalid_request` / 409 `resource_conflict`）。设计验证项 `VRC-MGMT-001`；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`T-CFG-CAS`、`CT-ADMIN-001`（[系统测试方案 §6 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）。
**不证明什么**：不证明更新/删除/If-Match（ST-PROV-005..10）、不证明 `kind`/`secret_ref` 负向（ST-PROV-011/12）、不证明 `usage` 子对象更新（ST-PROV-013）、不证明重名 409（本 case 用随机名避开）、不证明响应不含 secret 的强断言（ST-PROV-014）；
创建不触上游，故不证明 provider 可达性。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。执行前须满足[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) **附加（B 类）**：实例 `/healthz` 200；`_baseline_settings` 注入 1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier。fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）：`llmtier_b`、`admin_client_b`。初始状态：m5air 上级基线由 `_baseline_settings` 提供。**TS-003**：请求中的 `endpoint` 用 LAN 常量 `LAN_PROVIDER_ENDPOINT`（可用 `LLMTIER_TEST_PROVIDER_URL` 覆盖），**禁止 `127.0.0.1`**。创建不触上游，endpoint 仅在后续使用时可解析即可。

## 3. 输入构造

- **输入与构造**：固定请求（随机名避免与既有 provider 重名）：
  ```http
  POST /v1/providers HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-admin
  Content-Type: application/json
  ```
  ```json
  {
    "name": "Test Provider <uuid8>",
    "kind": "local",
    "endpoint": "http://192.168.1.9:9000/v1",
    "secret_ref": null,
    "enabled": true
  }
  ```
  构造点：`kind` ∈ `{cloud,local}`（本 case 取 `local`）；`secret_ref` 为 `null`（→ `has_secret=false`）；`enabled=true`；`name` 取 `Test Provider <uuid4 前 8 位>` 保证唯一；请求体键集 ⊆ `{name,kind,endpoint,secret_ref,enabled,usage}`。不注入故障；不构造非法输入（负向属 ST-PROV-011/12）。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` 启动并轮询 `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `resp = admin_client_b.post("/v1/providers", json=body)`；断言 `status_code == 201`。
  3. 解析 body（`ProviderView`）：断言 `name`/`kind`/`endpoint`/`enabled` 回显与请求一致；`id` 存在且为非空字符串；`version == 1`；`has_secret is False`；`usage`/`request_usage` 为对象。
  4. 断言响应头含 `ETag`，值等于 `"<id>.v1"`（格式 `"<resource_id>.v<N>"`，含双引号，[`registry._etag`](../../../../src/management/registry.py)）。
  5. `get_resp = admin_client_b.get(f"/v1/providers/{rid}")`；断言 `200`、`name` 一致、`get_resp.headers["ETag"] == create` 的 ETag（版本未推进）。
  6. （teardown，`finally` 内）以最新 `GET` 的 `ETag` 发 `DELETE /v1/providers/{rid}`，断言 `204`；再 `GET` 断言 `404`。

**重点关注步骤**：① **201 而非 200**——创建成功必须是 `201`，`ETag` 头必须存在；② **自动 id 与 version 初值**——`id` 由服务端生成、`version==1`，不得回显客户端未提供的字段为随机值；
③ **ETag 格式与版本一致性**——`"<id>.v1"` 含双引号，回读 ETag 与创建一致；④ **`has_secret` 语义**——`secret_ref=null` ⇒ `has_secret=false`，且响应体**不含** `secret_ref` 键（ST-PROV-014 的强断言）；
⑤ **拒绝零副作用**——若收到 400/409，须确认账本/资源无新建（本 case 用唯一名，不应命中 409）；⑥ **teardown 必达**——创建的 provider 无 deployment 引用，可安全 `DELETE`；
若 `DELETE` 412，先重新 `GET` 取新 ETag 再删。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ProviderView` + `ProviderWrite` + ETag 规则（不依赖实现细节）。
  - 创建：`201`；body `{id:"provider_<hex>",name,kind:"local",endpoint,has_secret:false,enabled:true,usage:…,request_usage:{calls:0,input_tokens:null,output_tokens:null,total_tokens:null},version:1}`；响应头 `ETag: "<id>.v1"`。
  - 回读：`GET /v1/providers/{id}` → `200`，同 `name`、同 `ETag`。
  - teardown：`DELETE`（正确 If-Match）→ `204`；随后 `GET` → `404 not_found`。
  - 无错误信封：成功路径不应出现 `{"error":{...}}`。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：创建 `201` + 自动 id + `version==1` + `has_secret==false` + ETag `"<id>.v1"`；回读 `200` 且 ETag 一致；teardown `DELETE 204` 且随后 `GET 404`。
  - **FAIL**：任一断言不符（status 非 201、缺 ETag、字段错、回读失败、teardown 未删净）——按[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则) 给预期 vs 实际与 `reproduction_cmd`。
  - **BLOCKED**：无法执行/无法判定且可重试（fixture 写不出、断言逻辑错、语义不清）——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：B 类临时实例不可用、依赖 fixture 未满足——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：以 `127.0.0.1` 作为新建 provider 的 `endpoint`（违反 TS-003）、或以 mock/替代路径冒充真实实例——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（计划 §3 实现盘点 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**必须 teardown（`finally` 强制）**——删除本 case 创建的 provider（`DELETE`，必要时先 `GET` 取新 ETag）；不修改 `prov_b`/`depl_b`、不写注入。B 类整班结束由 fixture `stop()` + `rm -rf` 销毁（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。离开前确认无本次创建物残留。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)：Run ID=`<date>/B-api`；保存请求与原始响应（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见计划 §7/§10；失败现场不截断。**本 case 额外证据**：创建请求/响应（status/headers 含 `ETag`/body）、回读响应、teardown 的 DELETE 与后续 GET。

- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；`ProviderWrite`/`ProviderView` 机器契约（`interfaces/openapi/llmtier.openapi.json`）；ETag 规则 `registry._etag`；自动化入口 [`ST-PROV-002.py`](../../../../tests/system/cases/ST-PROV-002.py)。**不依赖**其它 Case；与 ST-PROV-005..13 共享同一写路径但各自独立执行（每个 B 类写 case 自建/自清）。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
