<!-- STD_DOCUMENT_COVER_BEGIN -->
# ADM-SL-08 — 内部错误信封（非数组输入）

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ADM-SL-08` |
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
| Canonical Path | `docs/70_verification/specifications/cases/adm-sl-08.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ADM-SL-08`）；责任摘要、分类与优先级以 [系统测试方案 §3](../../schemes/llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 Service Level CRUD 接口（/v1/service-levels）（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-002`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ADM-SL-08` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ADM-SL-08` / 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） / `VRC-MGMT-002` / `recovery` / `P2`
- 方案清单登记：`ADM-SL-08`（与 §3.2 权威清单一致；本文件名 `adm-sl-08.md`，唯一对应）。
- 要测什么（责任展开）：`PATCH /v1/service-levels/{id}` 用非数组 `deployment_ids`：HTTP 500 `internal_error` 信封（无栈/无 secret）；同时登记"非法类型未预校验"缺陷。
- 明确不测什么 / 失败含义：不证明 合法 PATCH（ADM-SL-04）、不证明键白名单 400（ADM-SL-04b）、不证明能力/向量空间冲突 409（ADM-SL-06/07）、不证明审计/日志（ADM-AUDIT-01/ADM-LOGS-01）。本 case **不把 500 当正确行为**——它验证信封契约并登记缺陷。

**目的（被测契约）**：验证统一**服务器错误信封**在兜底 500 路径上的契约，并**登记**输入类型校验缺陷。被测端点/规则：`PATCH /v1/service-levels/{service_level_id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `updateServiceLevel`，`ServiceLevelPatch.deployment_ids` 类型应为 `array`）；[`registry.update_service_level`](../../../../src/management/registry.py) 只做键集校验（`set(body) <= {"deployment_ids","enabled"}`）**不做类型校验**，把 `deployment_ids` 直接交给 `_capability_intersection` 迭代；当其为非可迭代 JSON 类型（如整数）时抛 `TypeError`，被 [`app.py`](../../../../src/http_api/app.py) 的兜底 `except Exception` 转为 `ApiError(500, "internal_error", "Internal server error")`（5 键信封，[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。设计验证项 `VRC-MGMT-002`；错误目录 `ERR-INTERNAL` → wire `code=internal_error`；机制 `R-CFG-01`；需求/机制链 `LT-FUN-005`、`CT-ADMIN-001`。**不证明什么**：不证明合法 PATCH（ADM-SL-04）、不证明键白名单 400（ADM-SL-04b）、不证明能力/向量空间冲突 409（ADM-SL-06/07）、不证明审计/日志（ADM-AUDIT-01/ADM-LOGS-01）。本 case **不把 500 当正确行为**——它验证信封契约并登记缺陷。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 附加（B 类）；fixture `admin_client_b`（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；本 case 为 **MISSING**（§3.2 无 `at_adm_sl_08.py`），设计已写、实现待补。初始状态=`Worker` 存在。

## 3. 输入构造

- **输入与构造**：
  ```http
  PATCH /v1/service-levels/Worker HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-admin
  If-Match: "<从 GET 读取的真实 ETag>"
  Content-Type: application/json
  ```
  ```json
  {"deployment_ids": 1}
  ```
  构造点：`deployment_ids` 为 JSON **number**（非 array；非可迭代 → 触发 `TypeError`）；`If-Match` 取真实 ETag（使失败点落在类型处理而非 412）；body 键集仍 ⊆ 白名单（否则被 400 拦，无法到达 500 路径）。
  > **类型选择**：须用**非可迭代** JSON 类型（整数/布尔/null）才能命中 500。字符串会逐字符迭代并被当作未知 deployment 引用而返回 400 `invalid_request`、对象会迭代键同理——均**不**满足本 case 的 500 断言。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `get = admin_client_b.get("/v1/service-levels/Worker")`；断言 200；记 `etag`、`version_before`。
  3. `resp = admin_client_b.patch("/v1/service-levels/Worker", json={"deployment_ids": 1}, headers={"If-Match": etag})`。
  4. 断言 `resp.status_code == 500`；`err = resp.json()["error"]`：断言键集**恰为** `{message,type,code,param,retryable}`（无 `category`）、`err["code"]=="internal_error"`、`err["type"]=="server_error"`、`err["retryable"] is False`。
  5. 断言响应体**不含** Python traceback（`Traceback`/`File "`）、`TypeError`、`'int' object`、secret 字面 `9832`、`omlx-secret-key.txt`（脱敏校验）。
  6. （零副作用核验）`GET /v1/service-levels/Worker` 断言 `version==version_before`（异常在 `txn` 内抛出、事务回滚）。
  7. （缺陷登记）在 Run 报告写出缺陷记录：`deployment_ids` 缺失 JSON 类型预校验，非法类型未返回 400 `invalid_request` 而泄漏为 500 `internal_error`；`reproduction_cmd` 指向本 case 步骤 3。

**重点关注步骤**：① **命中真实 500 路径**——非数组、非可迭代输入导致 `_capability_intersection` 迭代 `TypeError`；字符串/对象会得 400，不能冒充本 case；② **信封 identity**——恰 5 键、`type` 由 500 导出为 `server_error`、`code=internal_error`；③ **不泄露**——body 不得含 traceback/内部类型信息/secret；④ **零副作用**——500 前事务必须回滚，`Worker.version` 不变；⑤ **现状与期望的区分**——500 是**已登记缺陷**的现状表现，PASS 判定的是"信封契约成立 + 缺陷被登记"，不是"500 是期望行为"；⑥ **审计**——失败经 `mutate` 记 `result="failed"`，属允许的审计记录。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ErrorEnvelope`/`ErrorDetail`（5 键）+ `ApiError.envelope` 的 `type` 由状态导出规则。
  - HTTP：`500`；`Content-Type: application/json`；body `{"error":{"message":"Internal server error","type":"server_error","code":"internal_error","param":null,"retryable":false}}`。
  - 脱敏：body 不含 traceback / `TypeError` / 内部类型字符串 / secret 字面。
  - 资源：`Worker.version` 不变。
  - 缺陷：Run 报告登记"非数组 `deployment_ids` 缺失类型预校验（应 400 `invalid_request`）"。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`500` + 恰 5 键信封 + `code=="internal_error"` + `type=="server_error"` + 无栈/无 secret；`Worker.version` 不变；缺陷已具名登记。
  - **FAIL**：status 非 500（如实现修复后返回 400——则须更新本 case 与 §3.2/§11.1 后再判）、信封键集不符、`code`/`type` 错、泄露内部信息、或 `Worker` 被改。
  - **BLOCKED**：无法执行/无法判定且可重试（实现尚未暴露该路径、断言不可实现）——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：B 类临时实例不可用——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 自动化入口 **`MISSING`**（§3.2），本轮未执行；缺口引用 §3.2/§9（MISSING ≠ NOT_RUN：无实现是缺口，不是跳过）。
  - **INVALID**：用 `127.0.0.1`/mock 冒充，或用字符串/对象等会得 400 的输入冒充 500 路径——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需业务 teardown**——500 前回滚，无资源改动。退出前确认 7 tier 齐全、`Worker.version` 未变、无注入残留。 B 类整班结束由 fixture `stop()` + `rm -rf` 临时目录（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存GET/PATCH 的请求与原始 500 响应（脱敏后）、`Worker` 前后 `version`、缺陷登记条目（含 `reproduction_cmd`）、发出命令、exit code、`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../../plans/llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/B-api`，`environment:"b"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b`（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）；`registry.update_service_level`/`_capability_intersection`（缺类型校验）；[`app.py`](../../../../src/http_api/app.py) 兜底 500；错误目录 `ERR-INTERNAL`；机制 `R-CFG-01`。自动化入口 **`MISSING`**（待补 `at_adm_sl_08.py`，落位按 §4.9/§8.5）。**不依赖**其它 Case；与 ADM-SL-04b（键白名单 400）互为"输入校验"的正/反例。

> 实现状态：Implemented（`at_adm_sl_08.py`）；执行状态与 Verdict 只在 Run 报告。

> **实现 vs 设计偏差（2026-09-30，已登记）**：本 case §1/§4/§5 的 500 `internal_error` 前提已过期。当前实现 [`registry._capability_intersection`](../../../../src/management/registry.py) 在迭代前显式校验 `deployment_ids` 必须是字符串数组（`registry.py:300`），非数组输入返回 **400 `invalid_request`（param=`deployment_ids`）**，不再抛 `TypeError` → 500。按本 case §5 的 FAIL 条款（"如实现修复后返回 400——则须更新本 case 与 §3.2/§11.1 后再判"），`at_adm_sl_08.py` 以**当前 code 行为**为 Oracle 断言 400 `invalid_request`，并核验零副作用（`Worker.version` 不变）。原"输入类型未预校验"缺陷已修复关闭；§1/§4/§5 的 500 描述待后续设计修订对齐。
