<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-SL-007 — 冻结向量空间冲突

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-SL-007` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-SL-007.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-SL-007`）；责任摘要、分类与优先级以 [系统测试方案 §3](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 Service Level CRUD 接口（/v1/service-levels）（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-002`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-SL-007` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-SL-007` / 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） / `VRC-MGMT-002` / `negative` / `P2`
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（ERR-EMBEDDING-SPACE）
- 方案清单登记：`ST-SL-007`（与 §3.2 权威清单一致；本文件名 `st-sl-007.md`，唯一对应）。
- 要测什么（责任展开）：`PATCH /v1/service-levels/Embedding-v1` 绑定非冻结向量空间的 embedding deployment：HTTP 409 `embedding_space_conflict`。
- 明确不测什么 / 失败含义：不证明 能力键缺失型的 `capability_conflict`（ST-SL-006）、不证明非 Embedding-v1 tier 的 responses 校验、不证明 embedding 数据面（ST-EMB-*）。

**目的（被测契约）**：验证 `Embedding-v1` 的**冻结 BGE-M3 向量空间契约**。被测端点/规则：`PATCH /v1/service-levels/{service_level_id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `updateServiceLevel`）；[`registry._validate_level`](../../../../src/management/registry.py) 对 `level_id=="Embedding-v1"` 要求 `embedding_space_id=="bge-m3-dense-1024-v1"`、`embedding_dimensions==[1024]`、`embedding_max_batch_inputs==32`、`embedding_max_input_tokens==8192`，否则 `raise ApiError(409, "embedding_space_conflict", …)`。设计验证项 `VRC-MGMT-002`；错误目录 `ERR-EMBEDDING-SPACE` → wire `code=embedding_space_conflict`；机制 `T-CFG-SPACE`；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`CT-ADMIN-001`。**不证明什么**：不证明能力键缺失型的 `capability_conflict`（ST-SL-006）、不证明非 Embedding-v1 tier 的 responses 校验、不证明 embedding 数据面（ST-EMB-*）。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 附加（B 类）；fixture `admin_client_b`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；初始状态=`Embedding-v1` 存在。

## 3. 输入构造

- **输入与构造**：先创建 embedding deployment（错误的 `embedding_space_id`），再 PATCH：
  ```http
  POST /v1/deployments HTTP/1.1
  Authorization: Bearer dev-admin
  ```
  ```json
  {"name":"Embedding Wrong Space","provider_id":"prov_b","backend_model":"embedding-model",
   "capabilities":{"responses":false,"embeddings":true,"tools":false,"structured_outputs":false,
   "input_modalities":["text"],"output_modalities":["text"],"context_window":4096,"max_output_tokens":2048,
   "embedding_space_id":"wrong-space-id","embedding_dimensions":[1024],"embedding_max_batch_inputs":32,
   "embedding_max_input_tokens":8192},
   "enabled":true}
  ```
  ```http
  PATCH /v1/service-levels/Embedding-v1 HTTP/1.1
  Authorization: Bearer dev-admin
  If-Match: "<从 GET 读取的真实 ETag>"
  ```
  ```json
  {"deployment_ids": ["<new_embedding_depl_id>"]}
  ```
  构造点：新 deployment `embeddings=true`、`responses=false` 使 `_validate_level` 先通过 embedding-only 校验，再在 `embedding_space_id` 冻结检查处失败（确保命中 `embedding_space_conflict` 而非 `capability_conflict`）。不注入故障。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `get = admin_client_b.get("/v1/service-levels/Embedding-v1")`；断言 200；记 `etag`、`version_before`、原 `deployment_ids`。
  3. `new_depl = admin_client_b.post("/v1/deployments", json={…})`；断言 `201`；记 `new_depl_id`、`new_depl_etag`。
  4. `resp = admin_client_b.patch("/v1/service-levels/Embedding-v1", json={"deployment_ids":[new_depl_id]}, headers={"If-Match": etag})`。
  5. 断言 `resp.status_code == 409`；`err = resp.json()["error"]`：断言 `err["code"]=="embedding_space_conflict"`、`err["type"]=="request_error"`、`err["retryable"] is False`。
  6. （零副作用核验）`GET /v1/service-levels/Embedding-v1` 断言 `deployment_ids` 与 `version` 均为原值。
  7. （teardown，`finally` 内）`DELETE /v1/deployments/{new_depl_id}`（最新 ETag）→ `204`；`GET` 断言 404。

**重点关注步骤**：① **命中正确分支**——`embedding_space_id` 错误但 embedding/responses 标志正确，必须得 `embedding_space_conflict`；若得 `capability_conflict` 说明构造使交集丢键（错误构造）；② **Embedding-v1 专属**——该冻结检查仅对 `level_id=="Embedding-v1"` 生效；③ **零副作用**——失败后 `Embedding-v1` 成员/版本不变；④ **teardown 完整性**——新建 embedding deployment 未被引用（PATCH 失败回滚），可删除；现有 [`ST-SL-007.py`](../../../../tests/system/cases/ST-SL-007.py) 已在 `finally` 内 `DELETE` 并断言 `204`/随后 `404`，同时回读 `Embedding-v1` 证明 `deployment_ids`/`version` 未变（零副作用）；⑤ **错误信封 identity**——恰 5 键、`type=request_error`。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ErrorEnvelope`/`ErrorDetail` + 冻结向量空间规则（[系统设计 §7.8](../../../20_system_design/llmtier-system-design.md)）。
  - POST deployment：`201` + ETag。
  - PATCH SL：`409`；body `{"error":{"message":"Embedding-v1 requires the frozen BGE-M3 vector space","type":"request_error","code":"embedding_space_conflict","param":null,"retryable":false}}`。
  - 回读：`Embedding-v1.deployment_ids` 与 `version` 不变。
  - teardown：`DELETE` new deployment → `204`；随后 `GET` → `404`。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：PATCH `409` + `code=="embedding_space_conflict"`；`Embedding-v1` 未变；teardown 删除新建 deployment 且回读 404。
  - **FAIL**：status/code 错、`Embedding-v1` 被改、或 teardown 未删净。
  - **BLOCKED**：fixture/断言逻辑问题——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：B 类临时实例不可用——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充，或未命中真实向量空间检查——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**必须 teardown（`finally` 强制）**——删除本 case 新建的 embedding deployment（最新 ETag；412 先重取），不改 `depl_b`/`Embedding-v1`、不写注入。现有脚本已实现该 teardown（`finally` 内 `DELETE` → `204` → `GET 404`）。退出前确认无残留 deployment、7 tier 齐全。 B 类整班结束由 fixture `stop()` + `rm -rf` 临时目录（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存GET/POST/PATCH/DELETE 的请求与原始响应（含 ETag 头，脱敏后）、`Embedding-v1` 前后对比、发出命令、exit code、`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/B-api`，`environment:"b"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）；`registry.update_service_level`/`_validate_level`；错误目录 `ERR-EMBEDDING-SPACE`；机制 `T-CFG-SPACE`。自动化入口 [`ST-SL-007.py`](../../../../tests/system/cases/ST-SL-007.py)。**不依赖**其它 Case；与 ST-SL-006 共享 PATCH 但校验分支不同。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
