<!-- STD_DOCUMENT_COVER_BEGIN -->
# HEALTH-06 — 健康端点无需鉴权

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `HEALTH-06` |
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
| Canonical Path | `docs/70_verification/specifications/cases/health-06.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。方案清单行见[系统测试方案 §3 覆盖分母与 Case 清单](../../schemes/llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`HEALTH-06` / 系统设计 §8 健康/就绪接口（/healthz、/readyz） / `VRC-API-002`（另记 `VRC-MGMT-003`） / `normal` / `P1`。本文件名 `health-06.md`，与 Case ID 唯一对应。
- 要测什么（责任展开）：在**未配置任何鉴权凭据**的临时实例上，`GET /healthz` 与 `GET /readyz` 在不带 `Authorization` 头时仍返回各自视图（200/503），不返回 401/403/`auth_not_configured`。
- 明确不测什么 / 失败含义：**不证明什么**——不证明受保护端点在未配置鉴权时的 503 `auth_not_configured`（AUTH-07）；不证明 A 类公共端点无 token 200（AUTH-05）；不证明 LAN trust 免登录路径（AUTH-01/04）；不证明 `readyz` 的 ready/degraded（HEALTH-02/03）；不触发 provider 计费调用（`LT-OPS-001`）。**失败含义＝健康端点免鉴权契约破坏**。

**目的（被测契约）**：验证 IF-HEALTH 的**免鉴权**契约。端点 `GET /healthz`、`GET /readyz`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) 均为 `security:[]`）。实现 [`app.py`](../../../../src/http_api/app.py) 在 `_dispatch()` 中于任何 `_auth()` 调用（[`app.py:193`](../../../../src/http_api/app.py) 起）**之前**处理两个端点（[`app.py:187-190`](../../../../src/http_api/app.py)），故健康路径完全不查询凭据配置。设计验证项 `VRC-API-002`/`VRC-MGMT-003`；机制 `T-TRUST-NOCFG`（未配置凭据时受保护端点的 503 语义）与 `T-TRUST-SHARED`（需求 `R-TRUST-04`；见 [access-trust 机制](../../../20_system_design/mechanisms/access-trust.md)）；需求链 `LT-FUN-006`/`LT-OPS-001`、`CT-OPS-001`（[系统测试方案 §3](../../schemes/llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）。**不证明什么**：不证明受保护端点在未配置鉴权时的 503 `auth_not_configured`（AUTH-07）；不证明 A 类公共端点无 token 200（AUTH-05）；不证明 LAN trust 免登录路径（AUTH-01/04）；不证明 `readyz` 的 ready/degraded（HEALTH-02/03）；不触发 provider 计费调用（`LT-OPS-001`）。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例，见[系统测试方案 §1 测试边界](../../schemes/llmtier-system-test-scheme.md)）。执行前必须满足方案 §5 **附加（B 类）**：临时实例可启动且 `GET /healthz` 200。fixture 见[系统测试方案 §4 共同机制](../../schemes/llmtier-system-test-scheme.md)：`llmtier_b_no_auth`（[`conftest.py`](../../../../tests/system/api_test_v03/conftest.py) `LLMTierInstance(_NO_AUTH_SETTINGS, dev_mode=False)`）——`dev_mode=False` 时**不设** `LLMTIER_DEV_MODE`/`LLMTIER_ADMIN_TOKEN`/`LLMTIER_DATA_TOKEN`，`_NO_AUTH_SETTINGS` 为三个空 section。**关键客户端约束**：必须使用**不携带 `Authorization` 的裸 `httpx.Client`**（如 `httpx.Client(base_url=llmtier_b_no_auth.base_url, timeout=...)`）；**不得复用 `admin_client_b_no_auth`**——该 fixture 由 `_make_client` 注入 `Authorization: Bearer dev-admin`（[`conftest.py`](../../../../tests/system/api_test_v03/conftest.py) `_make_client`），在未配置 token 的实例上会走 [`authenticate`](../../../../src/http_api/auth.py) → 503 `auth_not_configured`，与本 case 契约无关。初始状态 = 无 provider/deployment（`_NO_AUTH_SETTINGS` 合法 bootstrap）+ 7 个空 fixed tier；故 `not_ready`。
- **被测入口**：

  ```http
  GET /healthz HTTP/1.1
  Host: 127.0.0.1:<port>
  ```

  ```http
  GET /readyz HTTP/1.1
  Host: 127.0.0.1:<port>
  ```

- **初态构造（经公开入口）**：`llmtier_b_no_auth` 以 `_NO_AUTH_SETTINGS` 合法 bootstrap（三空 section），7 个空 fixed tier；不注入故障；不构造非法输入。
- **Fixture / 向量及版本**：`llmtier_b_no_auth` fixture 与 `_NO_AUTH_SETTINGS`；独立无头 `httpx.Client`（[系统测试方案 §4 共同机制](../../schemes/llmtier-system-test-scheme.md)）。
- **依赖的测试资产（tests.asset-design 文档）**：本阶段 `tests.asset-design` 文档尚未建立；B 类实例夹具契约见方案 §4，引用其版本而不复制字节。

## 3. 输入构造

- **输入与构造**：固定请求（均无 body、无查询参数、**无 `Authorization`**）：

  ```http
  GET /healthz HTTP/1.1
  Host: 127.0.0.1:<port>
  ```

  ```http
  GET /readyz HTTP/1.1
  Host: 127.0.0.1:<port>
  ```

  构造点：**完全缺省 `Authorization` 头**（不是空串、不是 `Bearer `）；实例**未配置任何 token**（`dev_mode=False` 且无 `LLMTIER_*_TOKEN`）；不注入故障；不构造非法输入。
- **规模 / 时间域**：两次 GET（可加一次受保护端点交叉核对）；无分页/并发；记录 `elapsed` 供报告。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b_no_auth` 启动并轮询 `/healthz` 200。
  2. 建立**无凭据**客户端：`client = httpx.Client(base_url=llmtier_b_no_auth.base_url, timeout=...)`，不设 `Authorization`。
  3. `r1 = client.get("/healthz")`：断言 `r1.status_code == 200`，body 键集 `{status, version}` 且 `status=="ok"`、`version` 非空字符串。
  4. `r2 = client.get("/readyz")`：断言 `r2.status_code in (200, 503)`（本实例为 503），body 键集 `{status, models}`，`status ∈ {ready,degraded,not_ready}`。
  5. 断言两个响应**均不是鉴权错误**：`status` 不为 401、不为 403；若为 503，其 body 不得是 `{"error":{"code":"auth_not_configured",...}}`——必须是 `HealthView`/`ReadinessView` 视图。
  6. （可选交叉核对，不改变本 case 判定）同一无凭据客户端请求一个**受保护**端点（如 `GET /v1/models`）以揭示本实例的鉴权配置状态；该行为归 AUTH-07/AUTH-*，本 case 不据其判定。
  7. （清理）整班结束时由 fixture `stop()` 销毁实例。

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | 启动 `llmtier_b_no_auth`，轮询 `/healthz` 200 | 实例就绪、无 token |
| 2 | 建无凭据 `httpx.Client`（不设 `Authorization`） | 发送头快照证明无凭据 |
| 3 | `GET /healthz` 断言 200 + 合法 `HealthView` | 响应体 |
| 4 | `GET /readyz` 断言 200/503 + 合法 `ReadinessView` | 响应体 |
| 5 | 断言两者均非 401/403，非 `auth_not_configured` 信封 | 响应体 |
| 6 | （可选）受保护端点交叉核对（归 AUTH-*） | 揭示鉴权配置状态，不改判定 |
| 7 | fixture `stop()` 销毁实例 | 无残留 |

**重点关注步骤**：① **裸客户端而非带 token 的 fixture**——`admin_client_b_no_auth` 带 `Bearer dev-admin` 会得到 503 `auth_not_configured`；用它会把"未配置鉴权"误判成"健康端点需鉴权"，必须用无头客户端。② **不把 503 当失败**——`/readyz` 在无 deployment 的实例上是**合法 503**（`not_ready`）；契约是"免鉴权"，不是"必 200"。③ **区分鉴权错误与就绪错误**——503 时必须检查 body 形态：`ReadinessView`（本 case PASS）vs `{"error":{"code":"auth_not_configured"}}`（AUTH-07 语义，本 case FAIL/构造错误）。④ **`/healthz` 始终 200**——它位于 bootstrap 检查与鉴权之前，是免鉴权的最强证据。⑤ **实现事实**——`unauthenticated_principal` 对 loopback/RFC1918 无头请求会无条件授予共享角色（[`auth.py`](../../../../src/http_api/auth.py)），但健康端点根本不调用它；本 case 的契约点在于**端点本身 `security:[]`、handler 不查凭据**，而非"共享角色恰好生效"。⑥ **不得声称 env 门控**——`LLMTIER_TRUSTED_LAN_MODE` 不被源码读取（[系统测试方案 §4 共同机制](../../schemes/llmtier-system-test-scheme.md)）。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `security:[]` 的公开端点语义 + 实现 [`app.py:187-190`](../../../../src/http_api/app.py)（健康路径先于 `_auth()`）+ [`src/http_api/health.py`](../../../../src/http_api/health.py) 的 `HealthView`/`ReadinessView` + 系统设计 §8.1 `/healthz` 与 `/readyz` 契约（`/readyz` 503 = `ReadinessView`，**不是** `ErrorEnvelope`）（[llmtier-system-design.md](../../../20_system_design/llmtier-system-design.md)）；`openapi` 的 `/readyz` 503 schema 已修正为 `ReadinessView`（`NotReady`），与代码/§8.1 一致（[`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)）；端点公开语义见[系统测试方案 §4 共同机制](../../schemes/llmtier-system-test-scheme.md)，不依赖实现内部状态。**判据语义以设计验证项 `VRC-API-002`/`VRC-MGMT-003` 为唯一权威**。
  - `GET /healthz`（无凭据）：`200`；body `{status:"ok", version:<非空字符串>}`。
  - `GET /readyz`（无凭据）：`200` 或 `503`；body 为合法 `ReadinessView`（键集恰为 `{status, models}`），`status ∈ {ready,degraded,not_ready}`；本实例为 `503 + {status:"not_ready", models:[7×unavailable]}`。
  - 两者均**不得**为 401 `authentication_required`、403 `permission_denied`，也不得为带 `code=auth_not_configured` 的错误信封。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：无凭据下 `/healthz` 200 + 合法 `HealthView`，且 `/readyz` 返回合法 `ReadinessView`（本实例 503 `not_ready`），两者均非鉴权错误信封。
  - **FAIL**：任一健康端点返回 401/403，或返回带 `auth_not_configured` 的错误信封，或返回体不是合法视图；给预期 vs 实际与 `reproduction_cmd`。
  - **BLOCKED**：**无法构造未配置鉴权的实例**——例如 `llmtier_b_no_auth` fixture 缺失/无法启动、无法在无 token 条件下保持健康端点可达；或测试代码/断言不可实现。本 case 当前 `自动化入口 = MISSING`（清单），无脚本时应记为缺口而非 PASS。
  - **SKIP**：B 类临时实例不可用等 §2 前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用带 token 的请求冒充"无凭据"判定，或以 mock/替代路径冒充真实实例——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 case `自动化入口 = MISSING`（清单），本轮未执行；缺口引用见[系统测试方案 §4 缺口裁决](../../schemes/llmtier-system-test-scheme.md)（MISSING ≠ NOT_RUN：无实现是缺口，不是跳过）。

## 6. 错误路径、副作用与清理

- **错误出口与表现**：构造错误（误用带 token 的 `admin_client_b_no_auth` 得到 `auth_not_configured` 503）是主要错误出口；按 §5 判 FAIL/BLOCKED 并保留失败现场。其余同因情形见 §5 BLOCKED。
- **副作用断言与清理**：B 类实例按方案 §4 由 fixture `stop()` + `shutil.rmtree` 临时目录销毁；本 case 只读健康端点，不创建/修改资源、不写注入。离开前确认无未清空注入项（本 case 不注入）。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[§4.8/§10](../../schemes/llmtier-system-test-scheme.md)：保存裸客户端的发送 headers 快照（证明**无** `Authorization`）、两请求的原始 HTTP status/headers/body、实例环境证据（确认未设 token / `dev_mode=False`）、`elapsed`；manifest 与报告落位（`tests/system/reports/...`）见 §4.8/§10（本 case `environment:"b"`）；失败现场不截断。
- **依赖**：`llmtier_b_no_auth` fixture 与 `_NO_AUTH_SETTINGS`（[系统测试方案 §4 共同机制](../../schemes/llmtier-system-test-scheme.md)）；独立无头 `httpx.Client`（不复用 `admin_client_b_no_auth`）；`HealthView`/`ReadinessView`（[`openapi`](../../../../interfaces/openapi/llmtier.openapi.json)）；实现 [`app.py:187-190`](../../../../src/http_api/app.py) 与 [`auth.py`](../../../../src/http_api/auth.py)；自动化入口 **`MISSING`**（清单，尚无脚本）。**不依赖**其它 Case；与 AUTH-05（A 类公共端点无 token 200）、AUTH-07（未配置鉴权下受保护端点 503）语义相邻但各自独立执行、互不关闭。

> 实现状态：Planned（自动化入口 `MISSING`，缺口见 §5 BLOCKED）；执行状态与 Verdict 只在 Run 报告。
