<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-HEALTH-003 — readyz degraded

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-HEALTH-003` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-HEALTH-003.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。方案清单行见[系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-HEALTH-003` / 系统设计 §8 健康/就绪接口（/healthz、/readyz） / `VRC-MGMT-003`（另记 `VRC-UTIL-001/002`） / `recovery` / `P1`。本文件名 `st-health-003.md`，与 Case ID 唯一对应。
- **测试方法（§1.5 方法表行）**：状态机驱动（就绪态构造 degraded）+ 契约字段比对
- 要测什么（责任展开）：`GET /readyz` 在某 tier 存在候选 deployment 但无 `healthy` 候选时返回 HTTP 503 + `ReadinessView{status:"degraded", models[7]}`（各 tier `availability="degraded"`）。
- 明确不测什么 / 失败含义：**不证明什么**——不证明全可用 `ready`（ST-HEALTH-002）、无候选 `not_ready`（ST-HEALTH-004）、bootstrap 失败（ST-HEALTH-005）；不证明探测/健康转换过程（`POST /v1/probes` 属 ST-PROBE-*）、不证明推理路由可用；不触发 provider 计费调用（`LT-OPS-001`）。**失败含义＝降级就绪聚合契约破坏**。

**目的（被测契约）**：验证 IF-HEALTH 的**降级就绪**契约。端点 `GET /readyz`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `getReadiness`）。实现 [`readiness_view`](../../../../src/http_api/health.py)：某 fixed tier 的候选 deployment 列表非空但 `health=="healthy"` 计数为 0 ⇒ 该 tier `availability="degraded"`；只要存在非 `unavailable` 且非全部 `available` ⇒ `status="degraded"`、HTTP 503。系统设计 §8.1 明确"bootstrap 成功后 deployments 初始 `health=unknown`，故先为 `degraded`"（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md)）。设计验证项 `VRC-MGMT-003`；机制 `T-OBS`（[observability 机制](../../../20_system_design/mechanisms/observability.md)）、`T-CFG-BOOT`/`R-CFG-02`（[config-lifecycle 机制](../../../20_system_design/mechanisms/config-lifecycle.md)）；需求链 `LT-FUN-006`/`LT-OPS-001`、`VRC-UTIL-001/002`、`CT-OPS-001`（[系统测试方案 §3](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）。**不证明什么**：不证明全可用 `ready`（ST-HEALTH-002）、无候选 `not_ready`（ST-HEALTH-004）、bootstrap 失败（ST-HEALTH-005）；不证明探测/健康转换过程、不证明推理路由可用；不触发 provider 计费调用（`LT-OPS-001`）。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例，见[系统测试方案 §1 测试边界](../llmtier-system-test-scheme.md)）。执行前须满足方案 §5 **附加（B 类）**：临时实例可启动且 `GET /healthz` 200。**当前状态：Implemented——fixture `llmtier_b_unprobed`（[`conftest.py`](../../../../tests/system/conftest.py)）与脚本 [`ST-HEALTH-003.py`](../../../../tests/system/cases/ST-HEALTH-003.py) 已落地并通过。** 本 case 需要一个**已 bootstrap 基线资源但未被探测**的实例（每个 tier 的 `deployment_ids` 指向 `depl_b`、`depl_b.health="unknown"`；等价于 `LLMTierInstance(_baseline_settings)` 且**不调用** `_probe_deployment`）。[`conftest.py`](../../../../tests/system/conftest.py) 提供该 fixture `llmtier_b_unprobed`：**scope=session** 的 `LLMTierInstance(_baseline_settings(provider_endpoint_b))`，`start()` 后**跳过** `_probe_deployment`，产出实例的 7 tier 均 `degraded`（`health=unknown`）。**不可用现有 fixture 替代**：`llmtier_b` 启动即 `_probe_deployment(depl_b)`→`healthy`，把 7 tier 全翻成 `available`（那是 ST-HEALTH-002 的 ready 形态）；`llmtier_b_empty` 是三个空 section 的合法 bootstrap，7 tier 无候选 ⇒ 全 `unavailable` ⇒ `not_ready`（那是 ST-HEALTH-004），**都不是** `degraded`；**不得复用** `llmtier_b`。TS-003：`prov_b.endpoint` 必须是本机 **LAN IP** 上的 fake provider（不得用 `127.0.0.1` 作为被测服务的上游 endpoint）。目标初始状态 = 1 provider（`prov_b`）/ 1 deployment（`depl_b`，`health="unknown"`）/ 7 fixed tier 且 `diagnostic_injections` 为空。
- **被测入口**：

  ```http
  GET /readyz HTTP/1.1
  Host: 127.0.0.1:<port>
  Accept: application/json
  ```

- **初态构造（经公开入口）**：构造"有候选但无健康候选"——由 bootstrap 插入 `depl_b` 时 `health` 初始为 `"unknown"`（[`registry.py`](../../../../src/management/registry.py) `bootstrap_settings` 的 `INSERT INTO deployments ... 'unknown'`），且 7 tier 的 `deployment_ids` 均为 `["depl_b"]`，故每 tier `candidates` 非空、`healthy` 计数为 0 ⇒ `availability="degraded"`。**不在本 case 调用 `POST /v1/probes`**（保持 `unknown`，避免翻成 `healthy`）。备选构造：探测指向不可达上游的 `depl_b` 使其 `health` 变为 `unhealthy`（仍 `degraded`，因候选存在而健康为 0）；但"未探测"更确定、无上游依赖，优先。不注入故障；不构造非法输入。
- **Fixture / 向量及版本**：`llmtier_b_unprobed` fixture 与 `_baseline_settings(provider_endpoint_b)`（LAN fake provider，TS-003）（[系统测试方案 §4 共同机制](../llmtier-system-test-scheme.md)）。
- **依赖的测试资产（tests.asset-design 文档）**：本阶段 `tests.asset-design` 文档尚未建立；B 类实例与 fake provider 夹具契约见方案 §4，引用其版本而不复制字节。

## 3. 输入构造

- **输入与构造**：固定请求（无 body、无查询参数、无 `Authorization`）：

  ```http
  GET /readyz HTTP/1.1
  Host: 127.0.0.1:<port>
  Accept: application/json
  ```

  构造点：构造"有候选但无健康候选"（见 §2 初态构造）；**不携带凭据**（端点 `security:[]`）。不注入故障；不构造非法输入。
- **规模 / 时间域**：单次 GET；无分页/并发；记录 `elapsed` 供报告。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b_unprobed` 以 `_baseline_settings` 启动并轮询 `GET /healthz` 200，**不**执行 `_probe_deployment`（`depl_b.health` 保持 `unknown`），故 `GET /readyz` 为 `degraded`（若观测到 `ready`，说明实例被误探测，判 BLOCKED/构造失败）。
  2. `GET /readyz`（上表）；记录 status、`Content-Type`、`X-Request-ID`、body。
  3. 断言 `resp.status_code == 503`。
  4. 解析 body：断言键集**恰为** `{status, models}`，`status == "degraded"`。
  5. 断言 `models` 长度为 7，`id` 集合恰为 `{Senior, Junior, Worker, Associate, Engineer, Executor, Embedding-v1}`。
  6. 断言每个 `models[]` 元素 `availability == "degraded"`（存在候选、无 healthy）；逐元素键集恰为 `{id, availability}`。
  7. （清理）整班结束时由 fixture `stop()` 销毁实例。

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 构造未探测基线实例（`llmtier_b_unprobed`）；轮询 `/healthz` 200，不 probe，确认初始 `/readyz` 为 degraded | 实例就绪且未被探测 |
| 2 | `GET /readyz` | status / headers / body |
| 3 | 断言 status == 503 | HTTP 状态 |
| 4 | 断言 `status == "degraded"` | 响应体 |
| 5 | 断言 `models` 长度 7，`id` 集合恰为 7 fixed tier | 响应体 |
| 6 | 断言每个元素 `availability == "degraded"` | 响应体 |
| 7 | fixture `stop()` 销毁实例 | 无残留 |

**重点关注步骤**：① **`degraded` 与 `not_ready`/`ready` 的区分**——`degraded` 要求"候选存在但无 healthy"；无候选是 `unavailable` ⇒ `not_ready`（ST-HEALTH-004），全 healthy ⇒ `ready`（ST-HEALTH-002）。构造错会把状态判错。② **不得复用 `llmtier_b`**——该 fixture 启动即 probe 成 `healthy`，会导致 `ready`；必须用未探测实例。③ **`status` 由聚合导出**——`ReadinessView.status` 不是独立字段，是 7 个 `availability` 的聚合；只断言 503 + status 而不逐 tier 校验会漏判。④ **字段集精确性**——`ReadinessView` `additionalProperties:false`，只允许 `{status, models}`；模型元素只允许 `{id, availability}`。⑤ **不得被错误信封冒充**——503 时必须确认 body 是 `ReadinessView` 而非 `{"error":...}`（本端点未鉴权、不走错误信封）。⑥ **TS-003**——`prov_b.endpoint` 必须为 LAN IP，构造失败时应 BLOCKED/SKIP 而非改用 `127.0.0.1` 冒充。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = 实现 [`src/http_api/app.py`](../../../../src/http_api/app.py) 的 `/readyz` 处理分支（[`app.py:188-190`](../../../../src/http_api/app.py)：503 返回 `ReadinessView`，**不是** `ErrorEnvelope`）+ [`src/http_api/health.py`](../../../../src/http_api/health.py) `readiness_view` 的聚合规则 + 系统设计 §8.1 `/readyz` 503 `ReadinessView{status:"degraded"|"not_ready", models:[...]}` 契约（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md)）；`openapi` 的 `/readyz` 503 schema 已修正为 `ReadinessView`（`NotReady`），与代码 + §8.1 一致（[`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)），故本 case 的 503 Oracle 以代码 + §8.1 为准，不依赖实现内部数据。**判据语义以设计验证项 `VRC-MGMT-003` 为唯一权威**。
  - HTTP：`503`；`Content-Type: application/json; charset=utf-8`；`X-Request-ID` 存在。
  - body：键集**恰为** `{status, models}`；`status=="degraded"`；`models` 长度 7，元素键集 `{id, availability}`，`id` = 7 个 fixed tier，`availability=="degraded"`。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==503` + `status=="degraded"` + `models` 恰为 7 个 fixed tier 且全 `degraded`。
  - **FAIL**：status/字段/聚合不符——含误为 `ready`（被探测）或 `not_ready`（无候选），或返回错误信封；给预期 vs 实际与 `reproduction_cmd`。
  - **BLOCKED**：仅在 `llmtier_b_unprobed` 不可启动、或实例被误探测成 healthy（无法保留 `health=unknown`）时判 BLOCKED/构造失败。fixture（`llmtier_b_unprobed`）与脚本（[`ST-HEALTH-003.py`](../../../../tests/system/cases/ST-HEALTH-003.py)）均已落地并通过，不再是当前状态。若实例根本起不来/`/healthz` 不就绪，属依赖失败，视情形 BLOCKED 或 SKIP。
  - **SKIP**：B 类临时实例不可用、`provider_endpoint_b` 无 LAN IP 可用（TS-003）等 §2 前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用 `127.0.0.1`/mock 当上游 endpoint，或以替代路径冒充真实临时实例——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 case 有实现（[`ST-HEALTH-003.py`](../../../../tests/system/cases/ST-HEALTH-003.py)），未执行时记 `NOT_RUN`；不得以未跑冒充 PASS。

## 6. 错误路径、副作用与清理

- **错误出口与表现**：构造失败（实例被误探测成 healthy、无法保留 `unknown`）是主要错误出口，表现为 `/readyz` 返回 `ready` 或错误信封；此时按 §5 判 FAIL/BLOCKED 并保留失败现场。其余同因情形见 §5 BLOCKED。
- **副作用断言与清理**：B 类实例按方案 §4 由 fixture `stop()` + `shutil.rmtree` 临时目录销毁；本 case 只读 `/readyz`，不创建/修改资源、不写注入。离开前确认无未清空注入项（本 case 不注入）。（本 case 无 A 类污染风险。）

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../llmtier-system-test-scheme.md)：保存实例启动参数/settings（`_baseline_settings` 内容，脱敏后）、确认"未探测"的证据（未调用 `POST /v1/probes` 的请求日志）、原始 HTTP status/headers/body、`elapsed`、环境快照（`/healthz` + `/readyz`）；manifest 与报告落位（`tests/system/reports/...`）见 §4.8/§10（本 case `environment:"b"`）；失败现场不截断。
- **依赖**：B 类 fixture `llmtier_b_unprobed`（[`conftest.py`](../../../../tests/system/conftest.py)：session-scope `LLMTierInstance(_baseline_settings(provider_endpoint_b))`，`start()` 后跳过 `_probe_deployment`）；**不可复用** `llmtier_b`（启动即 probe 成 `healthy`）。另依赖 `_baseline_settings`/`provider_endpoint_b`（LAN fake provider，TS-003）（[系统测试方案 §4 共同机制](../llmtier-system-test-scheme.md)）；`ReadinessView`（[`openapi`](../../../../interfaces/openapi/llmtier.openapi.json)）；实现 [`health.py`](../../../../src/http_api/health.py)；系统设计 §8.1 的 `degraded` 初始态（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md)）；自动化入口 [`ST-HEALTH-003.py`](../../../../tests/system/cases/ST-HEALTH-003.py)（`ST-HEALTH-004.py` 承接 ST-HEALTH-004，本 case 用 `ST-HEALTH-003.py`，不与其冲突）。**不依赖**其它 Case；与 ST-HEALTH-002/04/05 同入口但状态互斥。

> 实现状态：Implemented（`ST-HEALTH-003.py` 已断言 503 + `degraded` + 7×`degraded`）；执行状态与 Verdict 只在 Run 报告。
