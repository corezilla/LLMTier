<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-OBSREQTRACE-003 — 请求追踪负向（角色）

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-OBSREQTRACE-003` |
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
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/cases/ST-OBSREQTRACE-003.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`ST-OBSREQTRACE-003`）；责任摘要、分类与优先级以 [系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单) 清单行为准。
- **测试脚本的唯一依据**：编码者按本文档写测试代码，不需要回读方案或设计正文猜测意图。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-OBSREQTRACE-003` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-OBSREQTRACE-003` / 系统设计 §8 请求追踪接口（/v1/trace/{request_id}） / ``VRC-API-002` + `R-TRUST-02`` / `security` / `P1`
- **测试方法（§1.5 方法表行）**：鉴权/角色隔离冒烟（data→观测面 403）
- 方案清单登记：`ST-OBSREQTRACE-003`
- 要测什么（责任展开）：`GET /v1/trace/{request_id}` 以 `data` token 访问：HTTP 403 `permission_denied`，无信息泄露（不返回 404 的存在性差异）。
- 明确不测什么 / 失败含义：不证明 正向 trace（ST-OBSREQTRACE-001）、不证明未知 id 404（ST-OBSREQTRACE-002）、不证明无凭据/非法方案 401（ST-AUTH-010）、不证明别名命名空间需 admin（ST-AUTH-008，虽同思路）、不证明快照/统计角色负向（未单列）。

**目的（被测契约）**：验证单请求 trace 的**角色授权负向契约**。被测端点/规则：`GET /v1/trace/{request_id}` 属 Observability（admin 面），路由在 `_dispatch` 中经 `principal = self._auth("admin")` 解析；
`data` token 不匹配配置的 admin token → `authenticate` 抛 `ApiError(403, "permission_denied", "The credential is not authorized")`（[`src/http_api/auth.py`](../../../../src/http_api/auth.py)），**先于**资源存在性检查（因此对任意 id 都 403，不泄露该 id 是否存在）；
错误信封恰 5 键（`type="request_error"`，`retryable=false`）。设计验证项 `VRC-API-002` + `R-TRUST-02`；机制 `T-TRUST-SHARED`/`T-TRUST-LEAK`（[access-trust 机制](../../../20_system_design/mechanisms/access-trust.md)）；
错误目录 `ERR-AUTH-DENIED` → `permission_denied`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理) `ERR-AUTH-DENIED → ...、ST-OBSREQTRACE-003`；
§3.5 `/v1/trace/{id}` 覆盖 `permission_denied`）；需求链 `LT-INT-001`/`LT-SEC-001/003`、`R-TRUST-01..04`、`CT-WEBSEC-001`/`CT-ADMIN-001`（[系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）；
机器契约 [`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)（`Forbidden`，`security=AdminBearerAuth`）。
**不证明什么**：不证明正向 trace（ST-OBSREQTRACE-001）、不证明未知 id 404（ST-OBSREQTRACE-002）、不证明无凭据/非法方案 401（ST-AUTH-010）、不证明别名命名空间需 admin（ST-AUTH-008，虽同思路）、不证明快照/统计角色负向（未单列）。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `data`；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `api_client`（`data`，[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；对照可另用 `admin_client`（`admin`）。初始状态=§2.3 A 类基线；本 case 纯 GET、零写入，初态即终态。

## 3. 输入构造

- **输入与构造**：固定请求（无 body）：
  - 主：`GET /v1/trace/req_does_not_exist`、`Authorization: Bearer dev-data` → 期望 **403**（不是 404）。
  - 存在性不泄露对照：`GET /v1/trace/<真实 id>`、`Authorization: Bearer dev-data` → 期望 **403**（与未知 id 同状态，证明授权先于存在性）。
  - 别名对照（旁证）：`GET /tier/admin/v1/trace/req_does_not_exist`、`Bearer dev-data` → 期望 **403**（ST-AUTH-008 语义，本 case 仅作旁证）。
  - 正相对照：同 id 用 `Bearer dev-admin` → 未知 id 返回 **404 not_found**；证明该 id 确实不存在且 admin 可达（用于区分"403 是因为不存在"的误判）。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz`（§2.1，自动执行）。
  2. `api_client.get("/v1/trace/req_does_not_exist")` → 记录 status/body。
  3. 断言 `resp.status_code == 403`；`err = resp.json()["error"]`：键集恰 5、`err["code"]=="permission_denied"`、`err["type"]=="request_error"`、`err["retryable"] is False`。
  4. （存在性不泄露）取一条真实 `request_id`（经 `admin_client` 的 `GET /v1/diagnostics/traces?limit=1`）→ 以 `Bearer dev-data` 请求 → 断言同样 **403**（且 body 与步骤 2 等价，不出现 404/200 差异）。
  5. （对照）同一未知 id 用 `admin_client`（`Bearer dev-admin`）→ 断言 `404 not_found`，证明步骤 2 的 403 不是"资源不存在"的伪装。
  6. （别名旁证）`GET /tier/admin/v1/trace/req_does_not_exist` + `Bearer dev-data` → 断言 `403 permission_denied`。

**重点关注步骤**：① **授权先于存在性**——data token 对存在/未知 id 都应 403，**不得**因 id 不存在而返回 404（信息泄露）；这是本 case 核心。② **403 vs 401**——`Bearer dev-data` 形态合法但不是 admin 凭据 → **403**（不是 401；
401 属缺/非法凭据，ST-AUTH-010）。③ **错误信封 identity**——恰 5 键、`type=request_error`、`retryable=false`。④ **不泄露存在性**——两种 id 的响应体应一致（除 message 中可能无 id 信息）。
⑤ **admin 可达对照**——用 admin 证明端点本身可用且未知 id 为 404，排除把"端点整体坏"误判为授权拒绝。⑥ **别名同保护**——别名路径同样要求 admin（ST-AUTH-008），本 case 作旁证。⑦ **降级/存储**——`_UnavailableDiagnostics.trace` 在授权**之后**才执行，故不影响 403；
`503 usage_store_unavailable` 判 BLOCKED/SKIP（仅在 admin 对照路径可能出现）。自动化入口 `ST-OBSREQTRACE-003.py` 已实现。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `Forbidden`（`ErrorEnvelope`）+ access-trust 机制的角色语义（授权先于资源）。
  - data token 访问 `/v1/trace/{id}`（任意 id）：HTTP `403`；`Content-Type: application/json`；body `{"error":{"message":"The credential is not authorized","type":"request_error","code":"permission_denied","param":<string|null>,"retryable":false}}`（恰 5 键；`message` 措辞以实现为准）。
  - 存在性不泄露：真实 id 与未知 id 的 data 响应一致（均 403）。
  - 对照：admin 对未知 id → `404 not_found`。
  - 别名旁证：`/tier/admin/v1/trace/{id}` + data → 403。
  - **fail-open**：授权在诊断调用之前，降级不影响 403；若健康实例对 data token 返回 200/404 → **FAIL**；`503 usage_store_unavailable` 判 **BLOCKED/SKIP**。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：data token 对存在/未知 id 均 `403 + permission_denied`（无信息泄露）；admin 对照 404 正确；别名旁证 403。
  - **FAIL**：data token 返回 200/404、`code` 非 `permission_denied`、或对未知 id 与已知 id 状态不同（泄露存在性）。
  - **BLOCKED**：测试代码/契约问题、降级实例、存储不可达——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：无（自动化入口已实现；执行状态见 Run 报告）。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air，或未命中真实鉴权路径却按行为判定——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——纯 GET，零副作用。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存 data token 的 403 信封（未知与真实 id）、admin 对照 404、别名旁证、命令/exit code/`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 6 项就绪检查；`api_client`（data）/`admin_client`（admin）fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）；`ERR-AUTH-DENIED`；实现 [`src/http_api/auth.py`](../../../../src/http_api/auth.py)、[`src/http_api/app.py`](../../../../src/http_api/app.py)（OBS 路由统一 `_auth("admin")`）；access-trust 机制。自动化入口 `ST-OBSREQTRACE-003.py`（已实现）。**不依赖**其它 Case；与 ST-OBSREQTRACE-001/02（正向/404）、ST-AUTH-008（别名需 admin）互补但各自独立执行。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
