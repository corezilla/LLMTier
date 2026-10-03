<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-RUNTIME-002 — 运行时快照负向（角色）

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-RUNTIME-002` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-RUNTIME-002.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-RUNTIME-002`）；责任摘要、分类与优先级以 [系统测试方案 §6](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 运行态接口（GET /v1/runtime）（parent `llmtier-system-design`），设计验证项 `VRC-INF-004`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-RUNTIME-002` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-RUNTIME-002` / 系统设计 §8 运行态接口（GET /v1/runtime） / `VRC-INF-004` / `security` / `P1`
- **测试方法（§2.2 方法表行）**：鉴权/角色隔离冒烟（data→管理面 403）
- 方案清单登记：`ST-RUNTIME-002`（与 计划 §3 权威清单一致；本文件名 `st-runtime-002.md`，唯一对应）。
- 要测什么（责任展开）：`GET /v1/runtime` 携 data 角色有效凭据：HTTP 403 `permission_denied`（管理面角色隔离）。
- 明确不测什么 / 失败含义：不证明 成功快照（ST-RUNTIME-001）、不证明无凭据/非法方案 401（ST-AUTH-010）、不证明未配置鉴权 503（ST-AUTH-007）、不证明 LAN 免登录（ST-AUTH-004）。本 case **只**锁"有效 data 凭据 → 403"。

**目的（被测契约）**：验证管理端点对**已认证但角色不足**的拒绝契约。被测端点/规则：`GET /v1/runtime`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `getRuntimeSnapshot`，`security=AdminBearerAuth`）；
[`app.py`](../../../../src/http_api/app.py) 以 `self._auth("admin")` 守护 → [`auth.authenticate`](../../../../src/http_api/auth.py) 当 Bearer 值合法但等于 data token 时 `raise ApiError(403, "permission_denied", "The credential is not authorized")`。
设计验证项 `VRC-INF-004`；需求/机制链 `LT-INT-001`、`LT-SEC-001`、`R-TRUST-02`、`T-TRUST-SHARED`、`CT-ADMIN-001`。错误目录 `ERR-AUTH-DENIED` → wire `code=permission_denied`。
**不证明什么**：不证明成功快照（ST-RUNTIME-001）、不证明无凭据/非法方案 401（ST-AUTH-010）、不证明未配置鉴权 503（ST-AUTH-007）、不证明 LAN 免登录（ST-AUTH-004）。本 case **只**锁"有效 data 凭据 → 403"。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=计划 §3 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `api_client`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；本 case 自动化入口 [`ST-RUNTIME-002.py`](../../../../tests/system/cases/ST-RUNTIME-002.py) 已实现（计划 §3 实现盘点 `RUN`）。初始状态=§2.3 A 类基线；本 case 只读、无副作用。
  > **关键构造约束**：必须使用**显式且有效的 data bearer**（`Bearer dev-data`）。**不得**用"缺 `Authorization` 头"来构造 403——受信 LAN/loopback 的无头请求会被 [`unauthenticated_principal`](../../../../src/http_api/auth.py) 无条件授予**共享角色主体**（`trusted-lan-operator`/`trusted-lan-consumer`，本端点按 role=admin 解析为 operator），从而得到 200 而非 403（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。角色负向必须靠"有效但角色不符的凭据"。

## 3. 输入构造

- **输入与构造**：
  ```http
  GET /v1/runtime HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Accept: application/json
  ```
  构造点：显式 `Bearer dev-data`（有效 data 凭据，非 admin）；无 body、无 query；**不**省略 `Authorization` 头。不注入故障。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 计划 §2 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. （正向对照，非本 case 判定）`admin_client.get("/v1/runtime")` 断言 200（证明端点可用、403 来自角色而非端点缺失）。
  3. `resp = api_client.get("/v1/runtime")`（`api_client` 默认 `Bearer dev-data`）。
  4. 断言 `resp.status_code == 403`；`err = resp.json()["error"]`：断言 `err["code"]=="permission_denied"`、`err["type"]=="request_error"`、`err["retryable"] is False`。
  5. 断言 body 为错误信封（不含 `deployments`/`providers`/`queues`）——拒绝不得泄露快照内容。

**重点关注步骤**：① **有效凭据而非缺凭据**——必须显式发 `Bearer dev-data`；缺头会因 LAN trust 得 200，导致误判（ST-AUTH-004 正向）；② **403 而非 401**——凭据形态合法（`Bearer ` 前缀）、只是无权 → 403 `permission_denied`；
401 属缺/非法方案（ST-AUTH-010）；③ **拒绝先于 handler**——鉴权在 `_dispatch` 分派前完成，不得泄露 runtime body、不得触业务逻辑；④ **错误信封 identity**——恰 5 键、`type=request_error`；
⑤ **与 ST-AUTH-003 的关系**——ST-AUTH-003 覆盖 `GET /v1/providers` 的同类角色负向；本 case 是该负向在 `/v1/runtime` 的承接，二者独立执行。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ErrorEnvelope`/`ErrorDetail` + access-trust 角色规则（[access-trust 机制](../../../20_system_design/mechanisms/access-trust.md)）。
  - HTTP：`403`；body `{"error":{"message":"The credential is not authorized","type":"request_error","code":"permission_denied","param":null,"retryable":false}}`。
  - 无 runtime 快照字段泄露。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`403` + `code=="permission_denied"` + `type=="request_error"`，且 body 不含快照字段。
  - **FAIL**：status 非 403（含 200/401/503）、`code` 错、或泄露 runtime 内容。
  - **BLOCKED**：fixture/断言逻辑问题——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：计划 §3 前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（计划 §3 实现盘点 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。
  - **INVALID**：用缺 `Authorization` 头冒充角色负向（实际会因 LAN trust 得 200），或用 `127.0.0.1`/mock 冒充真实 m5air——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——只读负向，无状态变更。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存正向对照与负向请求的 headers 快照（证明发送 `Bearer dev-data`）、原始 403 响应（脱敏后）、发出命令、exit code、`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；`api_client` fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；`auth.authenticate`；错误目录 `ERR-AUTH-DENIED`；机制 `R-TRUST-02`/`T-TRUST-SHARED`。自动化入口 [`ST-RUNTIME-002.py`](../../../../tests/system/cases/ST-RUNTIME-002.py)。**不依赖**其它 Case；与 ST-RUNTIME-001（admin 正向）互补，与 ST-AUTH-003（`/v1/providers` 角色负向）同机制不同端点。

> 实现状态：Implemented（`ST-RUNTIME-002.py`）；执行状态与 Verdict 只在 Run 报告。
