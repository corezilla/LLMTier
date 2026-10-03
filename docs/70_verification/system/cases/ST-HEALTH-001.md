<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-HEALTH-001 — healthz 始终存活

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-HEALTH-001` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-HEALTH-001.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。方案清单行见[系统测试方案 §6 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-HEALTH-001` / 系统设计 §8 健康/就绪接口（/healthz、/readyz） / `VRC-API-002` / `normal` / `P0`。本文件名 `st-health-001.md`，与 Case ID 唯一对应。
- **测试方法（§2.2 方法表行）**：等价类划分 + 契约字段比对
- 要测什么（责任展开）：`GET /healthz` 公开存活探针：HTTP 200 + `HealthView{status:"ok", version:<string>}`，无凭据、无副作用；**即使 bootstrap/schema 失败也保持 200**。
  验证 IF-HEALTH 的**进程存活探针**契约。端点 `GET /healthz`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `getHealth`，`security:[]`），实现 [`src/http_api/app.py:187`](../../../../src/http_api/app.py) 在 `_dispatch()` 最前短路返回 `_json(200, health_view(__version__))`；
  [`health_view`](../../../../src/http_api/health.py) 返回 `{"status":"ok","version":<__version__>}`（`__version__="0.3.0-dev"`，[`src/http_api/__init__.py`](../../../../src/http_api/__init__.py)）。
  机制 `T-TRUST-ENDPOINTS`（需求 `R-TRUST-04`；见 [access-trust 机制](../../../20_system_design/mechanisms/access-trust.md)）；需求链 `LT-FUN-006`/`LT-OPS-001`、`CT-OPS-001`（[系统测试方案 §6/§5](../llmtier-system-test-scheme.md)）。
- 明确不测什么 / 失败含义：**不证明什么**——不证明就绪（`/readyz` 见 ST-HEALTH-002/03/04/05）；不证明 healthz 也经鉴权（该端点 `security:[]`，鉴权属 ST-AUTH-*）；不证明 `version` 的语义（只断言其为非空字符串）；不触发任何 provider 计费调用（`LT-OPS-001`）。**失败含义＝进程存活探针契约破坏**（返回非 200 或非 `HealthView`），而非就绪语义失败。

**目的（被测契约）**：验证 IF-HEALTH 的**进程存活探针**契约：`GET /healthz` 返回 200 + `HealthView`，且该端点 `security:[]`（无凭据）。**关键实现约束**：[`app.py:187`](../../../../src/http_api/app.py) 的 `/healthz` 分支位于 `if app.bootstrap_error`（[`app.py:192`](../../../../src/http_api/app.py)）之前，故即使 bootstrap 失败仍返回 200——它只代表进程存活。
设计验证项 `VRC-API-002`；机制 `T-TRUST-ENDPOINTS`；需求链 `LT-FUN-006`/`LT-OPS-001`、`CT-OPS-001`（[系统测试方案 §6 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）。
**不证明什么**：不证明就绪（`/readyz` 见 ST-HEALTH-002/03/04/05）；不证明 healthz 也经鉴权（该端点 `security:[]`，鉴权属 ST-AUTH-*）；不证明 `version` 的语义（只断言其为非空字符串）；
不触发任何 provider 计费调用（`LT-OPS-001`）。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 现有实例，角色 `none`；见[系统测试方案 §1 测试边界](../llmtier-system-test-scheme.md)）；前置 = 就绪检查（由 `conftest.py::pytest_configure` 自动执行，任一失败 → 整班 BLOCKED/SKIP）。初始状态 = m5air 现有 3 provider / 4 deployment / 7 fixed tier。本 case 纯读，不探测、不改 health。
- **被测入口**：

  ```http
  GET /healthz HTTP/1.1
  Host: 192.168.1.9:8181
  Accept: application/json
  ```

- **初态构造与客户端**：状态型初态无需构造（健康端点无内部状态依赖）；本 case 的零凭据契约点必须用**裸客户端**（**不用** `api_client`，其注入 `Authorization`）；具体 fixture/客户端构造见[系统测试方案 §4 测试环境类型](../llmtier-system-test-scheme.md)。
- **依赖的测试资产（tests.asset-design 文档）**：本阶段 `tests.asset-design` 文档尚未建立（系统测试资产以 `tests/system/conftest.py` 的 `LLMTierInstance` / `provider_endpoint_*` 夹具承载，契约见方案 §4）；引用其版本而不复制字节。

## 3. 输入构造

- **输入与构造**：固定请求（无 body、无查询参数、无 `Authorization`）：

  ```http
  GET /healthz HTTP/1.1
  Host: 192.168.1.9:8181
  Accept: application/json
  ```

  构造点：零凭据契约点必须用裸客户端构造——**带 `Authorization` 头即非零凭据**；本 case 的 `security:[]` 判定必须用不带任何头的裸请求（`httpx.get(base + "/healthz")` 或新建 `httpx.Client(base_url=base)`），并显式断言该请求**未附 `Authorization`**。不构造非法输入（非法 query/body 不在本 case 范围）；不注入故障。
- **规模 / 时间域**：单次 GET；无分页/并发；记录 `elapsed` 供报告。并发/耐久不在本 case（见方案 §4 裁剪）。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = httpx.get(base + "/healthz")` —— **裸客户端、不携带任何头**（**不得**用 `api_client`：它注入 `Authorization`，与零凭据契约点矛盾）；记录 status、`Content-Type`、`X-Request-ID`、body。
  3. 断言 `resp.status_code == 200`。
  4. 断言 `content-type` 含 `application/json`。
  5. 解析 body：断言键集**恰为** `{status, version}`（`HealthView` `additionalProperties:false`），`status == "ok"`，`version` 为**非空字符串**。
  6. （交叉核对，不改变本 case 判定）在环境快照中同时记录同一时刻 `/readyz` 的 status，用于说明存活与就绪的语义分离；本 case 不对 `/readyz` 做契约断言。

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 确认基线（由 `pytest_configure` 自动执行） | 就绪检查通过 |
| 2 | 裸客户端 `GET /healthz`（无任何头） | status / `Content-Type` / `X-Request-ID` / body；发送头快照证明无 `Authorization` |
| 3 | 断言 status == 200 | HTTP 状态 |
| 4 | 断言 `content-type` 含 `application/json` | 响应头 |
| 5 | 解析 body 键集恰为 `{status, version}`、`status=="ok"`、`version` 非空字符串 | 响应体 |
| 6 | 交叉核对同刻 `/readyz` status | 存活 vs 就绪语义分离 |

**重点关注步骤**：① **`version` 是字符串**——契约要求 `version:str`；现有 [`ST-HEALTH-001.py`](../../../../tests/system/cases/ST-HEALTH-001.py) 已断言 200 + `status=="ok"` + `version` 为非空字符串，本 case 与该断言一致。
② **200 的真实含义**——`/healthz` 只证明进程存活，**不是**就绪；不得把 200 当作可接流量。③ **零凭据（`security:[]`）**——本 case 的凭据点必须由**裸客户端**（无 `Authorization`）发出；
`api_client` 固定注入凭据，用它即失去零凭据语义（只有 ST-AUTH-005 覆盖无 token，本 case 也不得冒充）。④ **不得被错误信封冒充**——若返回非 200，需确认是可解释环境问题，而非把 `{"error":...}` 当 `HealthView` 读。
⑤ 不在此 case 断言 `/readyz` 的 tier 状态（属 ST-HEALTH-002..05）。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `HealthView`（[`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)），不依赖实现内部状态。**判据语义以设计验证项 `VRC-API-002` 为唯一权威**。
  - HTTP：`200`；响应头 `Content-Type: application/json; charset=utf-8`；`X-Request-ID` 存在。
  - body：JSON 对象，键集**恰为** `{status, version}`；`status=="ok"`；`version` 为非空字符串。
  - 无错误信封：不应出现 `{"error":{...}}`。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==200` 且 body 键集恰为 `{status,version}` 且 `status=="ok"` 且 `version` 为非空字符串。
  - **FAIL**：status ≠ 200，或 body 非合法 `HealthView`（键集/类型不符），或 `status ≠ "ok"`；给预期 vs 实际与 `reproduction_cmd`。
  - **BLOCKED**：测试代码/契约本身问题（如断言不可实现、fixture 不可用）——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：就绪前置不满足（m5air 不可达等）——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：以 `127.0.0.1`/mock/替代路径冒充 m5air 真实路径——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：Case 有实现（方案清单 `RUN`）但本轮未执行；不得补造为 PASS。

## 6. 错误路径、副作用与清理

- **错误出口与表现**：本 case 为纯读成功路径，无业务错误出口；若观测到非 200 或 `{"error":...}` 信封，按 §5 判 FAIL 并保留原始 status/headers/body 作为失败现场。bootstrap/schema 失败**不属本 case 的错误路径**（`/healthz` 在 `bootstrap_error` 检查前短路，仍返回 200），那是 ST-HEALTH-005 的语义。
- **清理与复位**：**无需 teardown**——纯读、无副作用、无凭据；不创建/修改 provider/deployment/service-level、不写注入、不写 usage/账本。退出前确认 `/readyz` 仍显示 7 tier 且无未清空注入项（本 case 不注入）；若被误跑于 B 类临时实例，则按[系统测试方案 §4 测试环境类型](../llmtier-system-test-scheme.md) 整班 `stop()` + `rm -rf` 临时目录。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[计划 §7/§10](../llmtier-system-test-scheme.md)：保存发命令、exit code、原始 HTTP status/headers/body、`elapsed`、环境快照（`/healthz`/`/readyz` + provider/deployment 列表）；manifest 与报告落位（`tests/system/reports/...`）见计划 §7/§10（本 case `environment:"a"`）；失败现场不截断。
- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；**裸 `httpx` 客户端**（`M5AIR_BASE` 直连、无 `Authorization`；**不用** `api_client`）；`HealthView` 机器契约（[`openapi`](../../../../interfaces/openapi/llmtier.openapi.json)）；自动化入口 [`ST-HEALTH-001.py`](../../../../tests/system/cases/ST-HEALTH-001.py)。**不依赖**其它 Case；与 ST-HEALTH-002 共享同一探测入口但语义独立（存活 vs 就绪）。

> 实现状态：Implemented（`ST-HEALTH-001.py` 已断言本 case 契约）；执行状态与 Verdict 只在 Run 报告。
