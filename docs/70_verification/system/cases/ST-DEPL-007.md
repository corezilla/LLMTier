<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-DEPL-007 — capabilities 未知字段

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-DEPL-007` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-DEPL-007.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-DEPL-007`）；责任摘要、分类与优先级以 [系统测试方案 §3](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 Deployment CRUD 接口（/v1/deployments）（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-001`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-DEPL-007` 可追到方案清单行与 Run 报告。

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-DEPL-007` / 系统设计 §8 Deployment CRUD 接口（/v1/deployments） / `VRC-MGMT-001` / `negative` / `P1`
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（ERR-*）
- 方案清单登记：`ST-DEPL-007`（与 §3.2 权威清单一致；本文件名 `st-depl-007.md`，唯一对应）。
- 要测什么（责任展开）：`POST /v1/deployments` 的 `capabilities` 含未知键：HTTP 400 + `error.code=="invalid_request"`、`param=="capabilities"`，统一错误信封，无副作用。
- 明确不测什么 / 失败含义：不证明 创建成功（ST-DEPL-002）、不证明缺字段（ST-DEPL-006）、不证明 provider 引用（ST-DEPL-008）、不证明 `provider_id` PATCH（ST-DEPL-009）；本 case 为纯负向，**不得**创建出任何 deployment。

**目的（被测契约）**：验证 Deployment **capabilities 键集封闭性的负向契约**。被测端点/规则：`POST /v1/deployments`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `createDeployment`），`capabilities` 为 `ModelCapabilities`（`additionalProperties:false`）；[`registry._validate_capabilities`](../../../../src/management/registry.py) 断言 `set(value) == CAPABILITY_KEYS`（12 键），多键即 `raise ApiError(400,"invalid_request",…,"capabilities")`。设计验证项 `VRC-MGMT-001`；错误目录 `ERR-REQ-VALIDATION`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；需求/机制链 `LT-FUN-005`、`LT-INT-008`、`R-CFG-01`、`CT-ADMIN-001`。**不证明什么**：不证明创建成功（ST-DEPL-002）、不证明缺字段（ST-DEPL-006）、不证明 provider 引用（ST-DEPL-008）、不证明 `provider_id` PATCH（ST-DEPL-009）；本 case 为纯负向，**不得**创建出任何 deployment。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)/§2.4）。执行前须满足[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go)(../llmtier-system-test-scheme.md) **附加（B 类）**：实例 `/healthz` 200；`_baseline_settings` 注入 1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier。fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）：`llmtier_b`、`admin_client_b`。初始状态：m5air 上级基线由 `_baseline_settings` 提供。

## 3. 输入构造

- **输入与构造**：`capabilities` 含 12 个合法键 + 1 个未知键 `unknown_field`：
  ```http
  POST /v1/deployments HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-admin
  Content-Type: application/json
  ```
  ```json
  {
    "name": "Bad Deployment Unknown Field",
    "provider_id": "prov_b",
    "backend_model": "test-model",
    "capabilities": {
      "responses": true, "embeddings": false, "tools": false, "structured_outputs": false,
      "input_modalities": ["text"], "output_modalities": ["text"],
      "context_window": 4096, "max_output_tokens": 2048,
      "embedding_space_id": null, "embedding_dimensions": null,
      "embedding_max_batch_inputs": null, "embedding_max_input_tokens": null,
      "unknown_field": true
    },
    "enabled": true
  }
  ```
  构造点：`capabilities` 为"合法 12 键 + 1 未知键"（`set` 不等 → 400）；`provider_id` 指向既存 `prov_b`；不注入故障。**顺序**：先 `require(set(body)==required)` 通过，再 `_validate_capabilities` 命中未知键。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `before = admin_client_b.get("/v1/deployments")`；记初始 deployment id 集合。**注**：该列表 GET（[`admin.page()`](../../../../src/management/admin.py)）会在 M007 `query_snapshots`/`query_snapshot_items` 落一条 10 分钟 TTL 的分页快照（即使无 `cursor`）。
  3. `resp = admin_client_b.post("/v1/deployments", json=<上表 body>)`；记录 status、body。
  4. 断言 `resp.status_code == 400`。
  5. `err = resp.json()["error"]`：键集恰 5 键；`err["code"] == "invalid_request"`、`err["type"] == "request_error"`、`err["param"] == "capabilities"`、`err["retryable"] is False`。
  6. 对 deployment 资源零副作用：`after = GET /v1/deployments`；断言 id 集合与 `before` 相同（未创建）。**注**：第 2/6 步列表 GET 各自会在 `query_snapshots` 落一条 10 分钟 TTL 的分页快照（`admin.page()`），属服务端读路径副作用、非 deployment 资源，报告须登记，**不得笼统声称"零写入"**；"no new rows" 检查只针对 `deployments` 表，不得据 `query_snapshots` 新增判 FAIL。

**重点关注步骤**：① **400 + code + param 三断言**——`param=="capabilities"` 定位字段；② **对 deployment 资源拒绝零副作用**——未知键在 INSERT 前被拒，第 6 步证明无新 deployment 行；但第 2/6 步列表 GET 会在 `query_snapshots` 落 10 分钟 TTL 分页快照（`admin.page()`），须登记该写入、**不得声称"零写入"**；③ **信封 identity**——恰 5 键、`type="request_error"`；④ **与缺字段区分**——本 case 是"多键"，ST-DEPL-006 是"缺键"，两者都必须 400 `invalid_request`，但**不得互相替代**；⑤ **不依赖 message 文本**——只断言 code/type/param/retryable。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ModelCapabilities` 封闭键集 + `ErrorEnvelope`/`ERR-REQ-VALIDATION`。
  - HTTP：`400`；`Content-Type: application/json`。
   - body：`{"error":{"code":"invalid_request","type":"request_error","param":"capabilities","retryable":false,"message":"<nonempty>"}}`（恰 5 键）。
   - 无 deployment 资源变化（第 2/6 步列表 GET 自身的 `query_snapshots` 分页快照写入不计为资源变化）。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`400` 且 `code=="invalid_request"`、`param=="capabilities"`、信封 5 键、`type=="request_error"`，且无新 deployment（`query_snapshots` 分页快照写入不算副作用）。
  - **FAIL**：status 非 400（如 201 未知键仍创建）、code/param 不符、信封缺/多键，或产生 deployment 资源副作用。
  - **BLOCKED**：无法执行/无法判定且可重试——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：B 类临时实例/fixture 不可用——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：伪造 400 或替代路径冒充——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——负向拒绝对 deployment 资源无写副作用。第/各步列表 GET 的 `query_snapshots` 分页快照（10 分钟 TTL）由服务端自身产生，B 类整班 `rm -rf` 临时目录时随库消失，无需手工删除。 退出前确认 deployment 集合未变、基线 `depl_b` 仍在、无未清空注入。B 类整班结束由 fixture `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)(../llmtier-system-test-scheme.md)：Run ID=`<date>/B-api`；保存请求与原始响应（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。**本 case 额外证据**：POST 请求/原始响应、请求前后 deployment 列表（证明零副作用）。
  > **脚本覆盖（已对齐）**：现有 [`ST-DEPL-007.py`](../../../../tests/system/cases/ST-DEPL-007.py) 断言 `400` + `code=="invalid_request"` + `param=="capabilities"` + 5 键信封 + `type=="request_error"` + `retryable is False`，并回读 deployment 集合证明零副作用。

- **依赖**：B 类 fixture `llmtier_b`/`admin_client_b`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）；基线 provider `prov_b`；`ModelCapabilities`/`ErrorEnvelope` 机器契约；实现 `src/management/registry.py` `_validate_capabilities`/`create_deployment`；自动化入口 [`ST-DEPL-007.py`](../../../../tests/system/cases/ST-DEPL-007.py)。**不依赖**其它 Case；与 ST-DEPL-006（缺字段）互补但各自独立执行。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
