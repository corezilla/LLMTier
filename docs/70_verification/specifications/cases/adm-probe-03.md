<!-- STD_DOCUMENT_COVER_BEGIN -->
# ADM-PROBE-03 — 探测未知 deployment

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ADM-PROBE-03` |
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
| Canonical Path | `docs/70_verification/specifications/cases/adm-probe-03.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ADM-PROBE-03`）；责任摘要、分类与优先级以 [系统测试方案 §3](../../schemes/llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 探测接口（POST /v1/probes）（parent `llmtier-system-design`），设计验证项 `VRC-DIAG-004`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ADM-PROBE-03` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ADM-PROBE-03` / 系统设计 §8 探测接口（POST /v1/probes） / `VRC-DIAG-004` / `negative` / `P1`
- 方案清单登记：`ADM-PROBE-03`（与 §3.2 权威清单一致；本文件名 `adm-probe-03.md`，唯一对应）。
- 要测什么（责任展开）：`POST /v1/probes` 带确认探测未知 deployment：HTTP 404 `not_found`。
- 明确不测什么 / 失败含义：不证明 缺确认的 400（ADM-PROBE-01）、不证明成功探测（ADM-PROBE-02）、不证明 provider 未知（无独立 case）、不证明认证负向（AUTH-03/09）。

**目的（被测契约）**：验证探测对**不存在 deployment** 的资源解析契约。被测端点/规则：`POST /v1/probes`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `probeDeployment`，`security=AdminBearerAuth`）；[`AdminService.probe`](../../../../src/management/admin.py) 通过确认门后 `self.registry.get_deployment(body["deployment_id"])`，[`registry.get_deployment`](../../../../src/management/registry.py) 对未知 id 抛 404 `not_found`。设计验证项 `VRC-DIAG-004`；错误目录 `ERR-NOTFOUND` → wire `code=not_found`；需求/机制链 `LT-FUN-005`、`LT-OPS-002`、`R-OBS-01`、`CT-ADMIN-001`。**不证明什么**：不证明缺确认的 400（ADM-PROBE-01）、不证明成功探测（ADM-PROBE-02）、不证明 provider 未知（无独立 case）、不证明认证负向（AUTH-03/09）。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 附加（B 类）；fixture `admin_client_b`（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；初始状态=仅有 `depl_b`，无其它 deployment。本 case 为 **MISSING**（§3.2 无 `at_adm_probe_03.py`），设计已写、实现待补。

## 3. 输入构造

- **输入与构造**：
  ```http
  POST /v1/probes HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-admin
  Content-Type: application/json
  ```
  ```json
  {"deployment_id": "does_not_exist", "confirm_external_call": true}
  ```
  构造点：`confirm_external_call=true` 使请求先通过确认门（否则被 400 拦，无法到达资源解析）；`deployment_id="does_not_exist"` 为不存在的 id。不注入故障。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. （负向前置）`GET /v1/deployments/does_not_exist` 断言 404（确认 id 确实不存在）。
  3. `resp = admin_client_b.post("/v1/probes", json={"deployment_id":"does_not_exist","confirm_external_call":True})`。
  4. 断言 `resp.status_code == 404`；`err = resp.json()["error"]`：断言 `err["code"]=="not_found"`、`err["type"]=="request_error"`、`err["retryable"] is False`。
  5. （零副作用核验）`GET /v1/deployments` 断言列表未变、无新建 deployment。

**重点关注步骤**：① **先确认后解析**——必须先通过确认门（`confirm_external_call=true`），否则得 `confirmation_required` 而非 `not_found`；本 case 锁定 `not_found`；② **404 而非 400**——未知 deployment 是资源不存在（404 `not_found`），不是输入校验 400（`invalid_request`）；③ **零副作用**——不触上游、不写 `probe_results`、不改任何 health；④ **错误信封 identity**——恰 5 键、`type=request_error`；⑤ **审计**——`AdminService.probe` 直接调用（非 `mutate`），本路径**不**写审计；不得期望审计行。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ErrorEnvelope`/`ErrorDetail` + `registry.get_deployment` 的 not_found 语义。
  - HTTP：`404`；body `{"error":{"message":"Deployment not found","type":"request_error","code":"not_found","param":null,"retryable":false}}`。
  - 资源：无新增/变更 deployment。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`404` + `code=="not_found"` + `type=="request_error"`，且无资源/上游副作用。
  - **FAIL**：status 非 404（含 400/200）、`code` 错、或产生副作用。
  - **BLOCKED**：fixture/断言逻辑问题——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：B 类临时实例不可用——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 自动化入口 **`MISSING`**（§3.2），本轮未执行；缺口引用 §3.2/§9（MISSING ≠ NOT_RUN）。
  - **INVALID**：用 `127.0.0.1`/mock 冒充，或未命中真实资源解析——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——未产生资源/health 变更。退出前确认 deployment 列表仍为 `{depl_b}`、无注入残留。 B 类整班结束由 fixture `stop()` + `rm -rf` 临时目录（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存GET/POST 请求与原始 404 响应（脱敏后）、发出命令、exit code、`elapsed`、环境快照（`/healthz` + deployment 列表前后）；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../../plans/llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/B-api`，`environment:"b"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b`（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）；`registry.get_deployment`；错误目录 `ERR-NOTFOUND`；机制 `R-OBS-01`。自动化入口 **`MISSING`**（待补 `at_adm_probe_03.py`，落位按 §4.9/§8.5）。**不依赖**其它 Case；与 ADM-PROBE-01/02 互补。

> 实现状态：Implemented（`at_adm_probe_03.py`）；执行状态与 Verdict 只在 Run 报告。
