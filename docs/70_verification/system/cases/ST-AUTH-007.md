<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-AUTH-007 — 未配置鉴权

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-AUTH-007` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-AUTH-007.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`ST-AUTH-007`）；责任摘要、分类与优先级以 [系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单) 清单行为准。
- **测试脚本的唯一依据**：编码者按本文档写测试代码，不需要回读方案或设计正文猜测意图。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-AUTH-007` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-AUTH-007` / 系统设计 §8 认证与授权跨切面（角色/LAN trust/无鉴权） / `VRC-MGMT-003` / `security` / `P0`
- **测试方法（§1.5 方法表行）**：鉴权/授权/脱敏冒烟 + 角色隔离
- 方案清单登记：`ST-AUTH-007`（与 §3.2 权威清单一致；本文件名 `st-auth-007.md`，唯一对应）。
- 要测什么（责任展开）：受保护端点 `GET /v1/models` 在**未配置任何 token**的实例上、携带未配置的 bearer 时返回 503 + `auth_not_configured`（运行期无凭据可用，拒绝而非放行）。
- 明确不测什么 / 失败含义：不证明 **错误 bearer** 在**已配置**实例上被拒（ST-AUTH-002）、**空 bearer** 被拒（ST-AUTH-006）、**data token 访问 admin 面**被拒（ST-AUTH-003）、**缺/非法凭据→401**（ST-AUTH-010）、**无 token 的 LAN trust** 免登录（ST-AUTH-001/04）。特别地，本 case **不**证明"未配置鉴权时公共端点也 503"——`/healthz`/`/readyz` 永不进入鉴权（ST-AUTH-005/ST-HEALTH-006）。

  > **构造诚实性（如何触发）**：B 类临时实例监听 `127.0.0.1`（loopback，`auth.py:33`），若请求**不带** `Authorization` 头，`unauthenticated_principal()` 会授予 loopback 共享主体而返回 200——**无法**用"完全无头"触发 503。因此本 case 通过 `admin_client_b_no_auth` fixture 特意携带一个**未配置**的 `Authorization: Bearer dev-admin`，使 `unauthenticated_principal()` 返回 `None` 从而进入 `authenticate()`，再由"无配置 token"抛 503。该 bearer 字面量为测试占位符，与 503 的成立无关（无任何 token 被配置）。

**目的（被测契约）**：验证 access-trust 机制的 **未配置鉴权运行期语义**。被测端点/规则：`GET /v1/models`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listModels`，securityScheme `BearerAuth`）；
入口 [`_auth()`](../../../../src/http_api/app.py) 先经 [`unauthenticated_principal()`](../../../../src/http_api/auth.py)（因请求带 `Authorization` 头而返回 `None`），再落入 [`authenticate()`](../../../../src/http_api/auth.py)：`_configured_token("data")` 在无 `LLMTIER_DATA_TOKEN` 且 `LLMTIER_DEV_MODE≠1` 时返回 `None`，于是抛 `ApiError(503, "auth_not_configured")`（`auth.py:49-51`）。
设计验证项 `VRC-MGMT-003`；机制 `T-TRUST-NOCFG`（机制需求 `R-TRUST-04`：env token 存在性、503 `auth_not_configured` 语义；见 [access-trust 机制 §12.2/§14.4 R-TRUST-04](../../../20_system_design/mechanisms/access-trust.md)）；
错误信封 `{error:{message,type,code,param,retryable}}`，`type` 由状态导出（503 ≥ 500 ⇒ `server_error`）。**不证明什么**：不证明 **错误 bearer** 在**已配置**实例上被拒（ST-AUTH-002）、**空 bearer** 被拒（ST-AUTH-006）、**data token 访问 admin 面**被拒（ST-AUTH-003）、**缺/非法凭据→401**（ST-AUTH-010）、**无 token 的 LAN trust** 免登录（ST-AUTH-001/04）。
特别地，本 case **不**证明"未配置鉴权时公共端点也 503"——`/healthz`/`/readyz` 永不进入鉴权（ST-AUTH-005/ST-HEALTH-006）。

  > **构造诚实性（如何触发）**：B 类临时实例监听 `127.0.0.1`（loopback，`auth.py:33`），若请求**不带** `Authorization` 头，`unauthenticated_principal()` 会授予 loopback 共享主体而返回 200——**无法**用"完全无头"触发 503。因此本 case 通过 `admin_client_b_no_auth` fixture 特意携带一个**未配置**的 `Authorization: Bearer dev-admin`，使 `unauthenticated_principal()` 返回 `None` 从而进入 `authenticate()`，再由"无配置 token"抛 503。该 bearer 字面量为测试占位符，与 503 的成立无关（无任何 token 被配置）。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 附加（B 类）；使用 `llmtier_b_no_auth` fixture：`LLMTierInstance(_NO_AUTH_SETTINGS, dev_mode=False)`，启动时清除全部 `LLMTIER_*` 环境变量（`conftest.py`），且 `dev_mode=False` **不**写 token/`LLMTIER_DEV_MODE`，故 `_configured_token()` 必返回 `None`。初始状态=空库（`_NO_AUTH_SETTINGS`：无 provider/deployment/service-level）；本 case 使用 `admin_client_b_no_auth` fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 3. 输入构造

- **输入与构造**：固定请求（无请求体、无查询参数）：
  ```http
  GET /v1/models HTTP/1.1
  Host: 127.0.0.1:<临时端口>
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：实例**未配置任何 token**（`dev_mode=False`：清除 `LLMTIER_*` 后不写 token/DEV_MODE；`LLMTIER_TRUSTED_LAN_MODE=1` 被重设但不参与鉴权）；请求**特意携带一个 bearer**（`dev-admin`）以绕开 loopback LAN trust、强制走 `authenticate()`；bearer 字面量不重要（无 token 可匹配）。不注入故障；不构造非法输入。**不得**把本 case 跑在 A 类 m5air（其已配置 token，会得 403 而非 503）。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. 启动/复用 `llmtier_b_no_auth`（fixture session-scope；`start()` 轮询 `/healthz` 至 200）。记录临时实例端口。
  2. （可选前置确认）断言该实例上 `X` 环境不含 token（fixture 语义保证）；不重复 A 类就绪检查。
  3. `resp = admin_client_b_no_auth.get("/v1/models")`；记录 status、headers、body。
  4. 断言 `resp.status_code == 503`（无可用凭据 ⇒ 503；**不是** 200/401/403）。
  5. 解析 body 的 `error` 信封，断言 `error.code == "auth_not_configured"`、`error.type == "server_error"`（503 ≥ 500）、`error.param is None`、`error.retryable is False`，且 `error` 恰含 5 个键。
  6. 断言 body **不含** `object=="list"`/`data` 等 `ModelList` 字段（拒绝路径不得返回业务载荷）。

**重点关注步骤**：① **必须携带 bearer**——loopback 无头请求会命中 LAN trust 得 200，只有头存在才能进入 `authenticate()` 观察 503；这是本 case 最易误判处；② **`dev_mode` 必须为 False**——若 `LLMTIER_DEV_MODE=1`，`_configured_token()` 会回退到 `dev-data`/`dev-admin` 而不再 503；
fixture 已保证；③ **不得跑于 A 类**——m5air 已配置 token，本 case 的 503 前提是其**未配置**，误跑会得 403（ST-AUTH-002 行为）而误判；④ **503 的 `type` 是 `server_error`**（不是 `request_error`），且信封恰 5 键；
⑤ **拒绝先于 dispatch**——503 在路由体之前，无上游调用、无账本义务；⑥ 不在此 case 断言 401/403 或公共端点行为。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = access-trust 的未配置语义本身——"受保护端点 + 无配置 token ⇒ 503 `auth_not_configured`（不静默放行、不 401/403）"。
  - HTTP：`503`；响应头含 `X-Request-ID`。
  - body：`{"error":{"message":<str>,"type":"server_error","code":"auth_not_configured","param":null,"retryable":false}}`，恰 5 键。
  - 无业务载荷：本 case 不应出现 `object=="list"` 或 `data`。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==503` 且 `error.code=="auth_not_configured"` 且 `error.type=="server_error"` 且信封恰 5 键。
  - **FAIL**：返回 200（未配置却放行）/401/403/其它 status，或 `error.code` 不符、信封缺/多键；须给预期 vs 实际与 `reproduction_cmd`。
  - **BLOCKED**：B 类临时实例无法启动/无法判定（fixture 写不出、断言逻辑错）——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：B 类附加前置不满足（临时实例不可用）——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：以 A 类 m5air、`127.0.0.1` mock 或已配置 token 的实例冒充"未配置鉴权"——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：Case 已定义但本轮未执行（含实现缺失）。

## 6. 错误路径、副作用与清理

- **清理与复位**：**由 fixture 负责**——`llmtier_b_no_auth` session-scope，测试结束 `stop()`（`terminate`→等待→必要时 `kill`）并 `shutil.rmtree` 临时目录（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。本 case 为只读 `GET`，不创建/修改资源。确认临时端口无遗留监听（`lsof`）。若 B 类进程无法终止，保留证据并判 BLOCKED（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存启动参数快照（证明 `dev_mode=False` 且无 `LLMTIER_*` token）、原始命令、发送 headers 快照（证明携带 bearer）、HTTP status/headers/body、临时实例端口、exit code、`elapsed`、`/healthz` 快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/B-api`，`environment:"b"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：B 类临时实例可启动（[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go)）；fixture `llmtier_b_no_auth` 与 `admin_client_b_no_auth`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)，[`conftest.py`](../../../../tests/system/conftest.py)）；自动化入口 [`ST-AUTH-007.py`](../../../../tests/system/cases/ST-AUTH-007.py)。**不依赖**其它 Case；与 ST-AUTH-002/ST-AUTH-003/ST-AUTH-010 构成"凭据状态→状态码"矩阵但各自独立执行、互不关闭。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
