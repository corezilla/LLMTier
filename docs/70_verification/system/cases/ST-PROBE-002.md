<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-PROBE-002 — 探测带确认

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-PROBE-002` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-PROBE-002.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-PROBE-002`）；责任摘要、分类与优先级以 [系统测试方案 §3](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 探测接口（POST /v1/probes）（parent `llmtier-system-design`），设计验证项 `VRC-DIAG-004`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-PROBE-002` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-PROBE-002` / 系统设计 §8 探测接口（POST /v1/probes） / `VRC-DIAG-004` / `normal` / `P1`
- **测试方法（§1.5 方法表行）**：等价类划分 + 契约字段比对
- 方案清单登记：`ST-PROBE-002`（与 §3.2 权威清单一致；本文件名 `st-probe-002.md`，唯一对应）。
- 要测什么（责任展开）：`POST /v1/probes` 带 `confirm_external_call=true`：HTTP 200 + `ProbeResult`（`deployment_id`/`status`/`checked_at`/`may_have_incurred_cost`）。
- 明确不测什么 / 失败含义：不证明 缺确认的 400（ST-PROBE-001）、不证明未知 deployment 的 404（ST-PROBE-003）、不证明 provider 目录（ST-PMOD-*）、不发布上游时延 SLO（本 case 只记录 `elapsed`）。

**目的（被测契约）**：验证**已确认探测**的成功契约与 health 落地。被测端点/规则：`POST /v1/probes`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `probeDeployment`，body `ProbeRequest`，`security=AdminBearerAuth`）；
[`AdminService.probe`](../../../../src/management/admin.py) 通过确认门后 `get_deployment`→`get_provider`→构造 `LocalProvider`/`OpenAIProvider`→`adapter.probe()`→`apply_probe_result(...)`（写 `deployments.health` 与 `probe_results`）→`audit.record("deployment.probe")`→返回 `{deployment_id,status,checked_at,may_have_incurred_cost}`。
设计验证项 `VRC-DIAG-004`；需求/机制链 `LT-FUN-005`、`LT-OPS-002`、`R-OBS-01`、`CT-ADMIN-001`、`CT-OPS-001`。**不证明什么**：不证明缺确认的 400（ST-PROBE-001）、不证明未知 deployment 的 404（ST-PROBE-003）、不证明 provider 目录（ST-PMOD-*）、不发布上游时延 SLO（本 case 只记录 `elapsed`）。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `admin_client`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；初始状态=`dep_local_gemma`（local provider）`health` 为 `healthy`（ready 基线）。本 case **会调上游探测**（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)：探测/费用须显式确认，执行者需授权）。

## 3. 输入构造

- **输入与构造**：
  ```http
  POST /v1/probes HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Content-Type: application/json
  ```
  ```json
  {"deployment_id": "dep_local_gemma", "confirm_external_call": true}
  ```
  构造点：body 键集**恰为** `{deployment_id, confirm_external_call}`（`admin.probe` 要求精确相等，多/少键→400）；`confirm_external_call is true`；选 local deployment `dep_local_gemma`（TS-003：其 provider endpoint 为 LAN/本机 local adapter，不引入 `127.0.0.1` 上游）。不注入故障。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. （前置快照）`GET /v1/deployments/dep_local_gemma`；记 `health_before`、`version_before`。
  3. `resp = admin_client.post("/v1/probes", json={"deployment_id":"dep_local_gemma","confirm_external_call":True})`。
  4. 断言 `resp.status_code == 200`；`body = resp.json()`：断言键集**恰为** `{deployment_id,status,checked_at,may_have_incurred_cost}`（`ProbeResult.additionalProperties:false`）；`deployment_id=="dep_local_gemma"`、`status in {"healthy","degraded","unhealthy"}`、`checked_at` 为 RFC3339 字符串、`may_have_incurred_cost` 为 bool。
  5. （health 落地核验）`GET /v1/deployments/dep_local_gemma` 断言 `health == body["status"]`（`apply_probe_result` 已写入）。
  6. （可选）`GET /v1/audit?limit=5` 断言出现 `action=="deployment.probe"`、`target=="dep_local_gemma"`、`result=="success"` 的审计行。

**重点关注步骤**：① **精确键集**——`admin.probe` 要求 `set(body)=={deployment_id,confirm_external_call}`；多余键（如加 `"foo"`）须 400 `confirmation_required`，不得误当成功；
② **真实上游调用与命中**——本 case 是真探测（非注入），`status` 来自 `adapter.probe()`，不能以 mock 替代；③ **health 落地**——响应 `status` 必须等于 `GET deployment` 的 `health`（证明探测结果写库），这是与"仅返回 status"的关键区别；
④ **副作用范围**——探测写 `deployments.health` 与 `probe_results`（按 deployment upsert）、写审计与 operational log；**不改 `version`**（`apply_probe_result` 不更新 version）；
⑤ **`may_have_incurred_cost`**——OpenAPI 仅为 bool；当前实现硬编码 `False`（即使真实探测可能计费），断言 bool 存在，**不断言其业务真值**，并在报告中记录该实现事实；⑥ **teardown 自恢复性**——探测是幂等观测，重跑得同一 health，无需资源删除。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ProbeResult` + 确认规则 + health 落地一致性。
  - HTTP：`200`；body 键集恰 `{deployment_id,status,checked_at,may_have_incurred_cost}`。
  - 一致性：`GET deployment.health == body.status`。
  - 审计：出现 `deployment.probe` success 行（可选交叉核对）。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`200` + `ProbeResult` 键集/类型正确 + `deployment_id` 匹配 + `status∈{healthy,degraded,unhealthy}` + `GET deployment.health` 与之一致。
  - **FAIL**：status 非 200、键集不符、`status` 非法、或 health 与响应不一致。
  - **BLOCKED**：上游不可达导致 `adapter.probe()` 抛错且无法判定（若属 §2.1 就绪则 SKIP）——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足（OMLX 离线、m5air 不可达）——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实探测，或未真正调用上游却按行为判定——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**观测型，无破坏性 teardown**——本 case 不创建/删除 provider/deployment/service-level；探测把 `dep_local_gemma.health` 置为其真实状态、写一条 `probe_results`（按 deployment upsert，无累积）与审计/日志（append-only）。退出前确认 `GET /v1/deployments/dep_local_gemma.health` 与初态一致、`/readyz` 仍 7 tier。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存POST 请求与原始 200 响应（脱敏后）、探测前后 `GET deployment`（`health`/`version`）、审计交叉核对、发出命令、exit code、`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；`admin_client` fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）；`ProbeRequest`/`ProbeResult` 机器契约；`AdminService.probe`/`apply_probe_result`；`dep_local_gemma` + 其 local provider；机制 `T-OBS`/`R-OBS-01`。自动化入口 [`ST-PROBE-002.py`](../../../../tests/system/cases/ST-PROBE-002.py)。**不依赖**其它 Case；与 ST-PROBE-001/03 互补但各自独立执行。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
