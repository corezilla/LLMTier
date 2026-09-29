<!-- STD_DOCUMENT_COVER_BEGIN -->
# HEALTH-02 — readyz 就绪=全部 tier 可用

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `HEALTH-02` |
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
| Canonical Path | `docs/70_verification/specifications/cases/health-02.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。方案清单行见[系统测试方案 §3 覆盖分母与 Case 清单](../../schemes/llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`HEALTH-02` / 系统设计 §8 健康/就绪接口（/healthz、/readyz） / `VRC-MGMT-003`（另记 `VRC-UTIL-001/002`） / `normal` / `P0`。本文件名 `health-02.md`，与 Case ID 唯一对应。
- 要测什么（责任展开）：`GET /readyz` 在全部 7 个 fixed tier 均 `available` 时返回 HTTP 200 + `ReadinessView{status:"ready", models[7]}`。
- 明确不测什么 / 失败含义：**不证明什么**——不证明降级 `degraded`（HEALTH-03）、无 deployment `not_ready`（HEALTH-04）、bootstrap 失败（HEALTH-05）、health 端点的鉴权行为（HEALTH-06/AUTH-05）；不证明 `models[]` 中每 tier 的路由/推理可用（只证明 readiness 聚合字段）；不触发 provider 计费调用（`LT-OPS-001`）。**失败含义＝就绪聚合契约破坏**。

**目的（被测契约）**：验证 IF-HEALTH 的**就绪聚合**契约。端点 `GET /readyz`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `getReadiness`，`security:[]`，200 = `ReadinessView`）。实现 [`readiness_view`](../../../../src/http_api/health.py) 对 7 个 `FIXED_TIERS` 逐个聚合：某 tier 的候选 deployment `health=="healthy"` 计数 >0 ⇒ `availability="available"`；全部 7 个 `available` ⇒ `status="ready"`、HTTP 200（否则 503，见 HEALTH-03/04/05）。设计验证项 `VRC-MGMT-003`；机制 `T-OBS`（见 [observability 机制](../../../20_system_design/mechanisms/observability.md)）与 `T-CFG-BOOT`/`R-CFG-02`（见 [config-lifecycle 机制](../../../20_system_design/mechanisms/config-lifecycle.md)）；需求链 `LT-FUN-006`/`LT-OPS-001`、`VRC-UTIL-001/002`、`CT-OPS-001`（[系统测试方案 §3 覆盖分母与 Case 清单](../../schemes/llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）。**不证明什么**：不证明降级 `degraded`（HEALTH-03）、无 deployment `not_ready`（HEALTH-04）、bootstrap 失败（HEALTH-05）、health 端点的鉴权行为（HEALTH-06/AUTH-05）；不证明 `models[]` 中每 tier 的路由/推理可用（只证明 readiness 聚合字段）；不触发 provider 计费调用（`LT-OPS-001`）。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 现有实例，角色 `none`，见[系统测试方案 §1 测试边界](../../schemes/llmtier-system-test-scheme.md)）；前置 = 就绪检查（含 `/readyz` 200 + 7 fixed tier；由 `conftest.py::pytest_configure` 自动执行，任一失败 → 整班 BLOCKED/SKIP）。初始状态 = m5air 现有 3 provider / 4 deployment / 7 fixed tier，且 7 tier 均已探测为 `healthy`（否则不就绪，本 case 无法达成 ready）。本 case 纯读，不探测、不改 health。
- **被测入口**：

  ```http
  GET /readyz HTTP/1.1
  Host: 192.168.1.9:8181
  Accept: application/json
  ```

- **初态构造与客户端**：状态型初态由 m5air 基线资源与既有探测保证（不在本 case 重新 probe）；本 case 的零凭据契约点必须用**裸客户端**（**不用** `api_client`，其注入 `Authorization`）；具体 fixture/客户端构造见[系统测试方案 §4 共同机制](../../schemes/llmtier-system-test-scheme.md)。
- **依赖的测试资产（tests.asset-design 文档）**：本阶段 `tests.asset-design` 文档尚未建立（系统测试资产以 `tests/system/api_test_v03/conftest.py` 的 `LLMTierInstance` / `provider_endpoint_*` 夹具承载，契约见方案 §4）；引用其版本而不复制字节。

## 3. 输入构造

- **输入与构造**：固定请求（无 body、无查询参数、无 `Authorization`）：

  ```http
  GET /readyz HTTP/1.1
  Host: 192.168.1.9:8181
  Accept: application/json
  ```

  构造点：零凭据（端点 `security:[]`）——本 case 的凭据点必须由**裸客户端**（无 `Authorization`）发出，`api_client` 固定注入凭据不可用于此；不构造非法输入；不改任何 deployment 的健康状态（`ready` 由 m5air 基线资源与既有探测保证）。
- **规模 / 时间域**：单次 GET；无分页/并发；记录 `elapsed` 供报告。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = httpx.get(base + "/readyz")` —— **裸客户端、不携带任何头**（**不得**用 `api_client`）；记录 status、`Content-Type`、`X-Request-ID`、body。
  3. 断言 `resp.status_code == 200`。
  4. 解析 body：断言 `status == "ready"`。
  5. 断言 `models` 为长度 **7** 的数组，元素 `id` 集合**恰为** `{Senior, Junior, Worker, Associate, Engineer, Executor, Embedding-v1}`（与 `FIXED_TIERS` 一致）。
  6. 断言每个 `models[]` 元素的 `availability == "available"`。
  7. （交叉核对）与 `GET /v1/models` 的 7 个 fixed tier 数量比对，佐证同一固定 tier 集合；本 case 不承担 `/v1/models` 的契约断言。

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 确认基线（`pytest_configure` 自动执行） | 就绪检查通过 |
| 2 | 裸客户端 `GET /readyz` | status / headers / body |
| 3 | 断言 status == 200 | HTTP 状态 |
| 4 | 断言 `status == "ready"` | 响应体 |
| 5 | 断言 `models` 长度 7，`id` 集合恰为 7 fixed tier | 响应体 |
| 6 | 断言每个元素 `availability == "available"` | 响应体 |
| 7 | 与 `/v1/models` 数量交叉核对（不改判定） | 佐证同一固定 tier 集合 |

**重点关注步骤**：① **`status` 必须是 `"ready"` 而非仅 200**——200 与 ready 在本实现同生，但仍显式断言 `status=="ready"`。② **7 是精确数**——固定 7 项；现有 [`at_obs_02.py`](../../../../tests/system/api_test_v03/at_obs_02.py) 已断言 `len(models)==len(FIXED_TIERS)` 且 `ids==set(FIXED_TIERS)`（无缺无多），本 case 与该断言一致。③ **每 tier 必须 `available`**——任何 `degraded`/`unavailable` 都使整体不为 ready，须按对应 Case（HEALTH-03/04）处理，不得在本 case 判 PASS。④ **不得被错误信封冒充**——非 200 时确认是可解释状态（degraded/not_ready 的 `ReadinessView`，或环境错误），而非把 `{"error":...}` 当就绪体。⑤ **字段集**——`ReadinessView` `additionalProperties:false`，只允许 `{status, models}`；每个模型元素只允许 `{id, availability}`。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ReadinessView` + `/readyz` 状态定义（[`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)、[系统测试方案 §5](../../schemes/llmtier-system-test-scheme.md)），与 m5air 具体数据无关。**判据语义以设计验证项 `VRC-MGMT-003` 为唯一权威**。
  - HTTP：`200`；`Content-Type: application/json; charset=utf-8`；`X-Request-ID` 存在。
  - body：键集**恰为** `{status, models}`；`status=="ready"`；`models` 长度 7，元素键集**恰为** `{id, availability}`，`id` = 7 个 fixed tier，`availability=="available"`。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==200` + `status=="ready"` + `models` 恰为 7 个 fixed tier 且全 `available`。
  - **FAIL**：status ≠ 200，或 `status ≠ "ready"`，或 tier 集合/长度不符，或存在非 `available` 的 tier；给预期 vs 实际与 `reproduction_cmd`。
  - **BLOCKED**：测试代码/契约本身问题——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：就绪前置不满足（m5air 不可达、`/readyz` 非 7 tier 就绪等）——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：以 `127.0.0.1`/mock/替代路径冒充 m5air 真实路径——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：Case 有实现（方案清单 `RUN`）但本轮未执行；不得补造为 PASS。

## 6. 错误路径、副作用与清理

- **错误出口与表现**：本 case 为纯读成功路径；非 200/非法 body 时按 §5 判 FAIL 并保留失败现场。状态互斥（ready / degraded / not_ready）见 HEALTH-03/04/05。
- **清理与复位**：**无需 teardown**——纯读、无副作用、无凭据；不创建/修改资源、不写注入、不改 deployment health。退出前确认 `/readyz` 仍显示 7 tier 且无未清空注入项（本 case 不注入）；若被误跑于 B 类临时实例，则按[系统测试方案 §4 共同机制](../../schemes/llmtier-system-test-scheme.md) 整班销毁。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../../schemes/llmtier-system-test-scheme.md)：保存命令、exit code、原始 HTTP status/headers/body、`elapsed`、环境快照（`/healthz`/`/readyz` + provider/deployment 列表）；manifest 与报告落位（`tests/system/reports/...`）见 §4.8/§10（本 case `environment:"a"`）；失败现场不截断。
- **依赖**：[系统测试计划 §3 执行前检](../../plans/llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；**裸 `httpx` 客户端**（`M5AIR_BASE` 直连、无 `Authorization`；**不用** `api_client`）；`ReadinessView`（[`openapi`](../../../../interfaces/openapi/llmtier.openapi.json)）；实现 [`health.py`](../../../../src/http_api/health.py)；自动化入口 [`at_obs_02.py`](../../../../tests/system/api_test_v03/at_obs_02.py)。**不依赖**其它 Case；与 HEALTH-03/04/05 同入口但状态互斥。

> 实现状态：Implemented（`at_obs_02.py` 已断言本 case 契约）；执行状态与 Verdict 只在 Run 报告。
