<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-AUTH-002 — 错误 bearer

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-AUTH-002` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-AUTH-002.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`ST-AUTH-002`）；责任摘要、分类与优先级以 [系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单) 清单行为准。
- **测试脚本的唯一依据**：编码者按本文档写测试代码，不需要回读方案或设计正文猜测意图。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-AUTH-002` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-AUTH-002` / 系统设计 §8 认证与授权跨切面（角色/LAN trust/无鉴权） / `VRC-API-002` / `security` / `P0`
- **测试方法（§1.5 方法表行）**：鉴权/授权/脱敏冒烟 + 角色隔离
- 方案清单登记：`ST-AUTH-002`（与 §3.2 权威清单一致；本文件名 `st-auth-002.md`，唯一对应）。
- 要测什么（责任展开）：`GET /v1/models` 在**携带 Authorization 头但 bearer 值错误**时被拒，返回 403 + `permission_denied`（凭据不匹配 ≠ 缺凭据）。
- 明确不测什么 / 失败含义：不证明 **空 bearer** 被拒（ST-AUTH-006）、**无 Authorization 头**的 LAN trust 免登录（ST-AUTH-001）、**data token 访问 admin 面**被拒（ST-AUTH-003）、**管理面未授权优先于资源存在性**（ST-AUTH-009）、**未配置鉴权→503**（ST-AUTH-007）、**缺/非法凭据→401**（ST-AUTH-010）；也不证明 `hmac.compare_digest` 的恒定时间性（INV-2 需专门时序测量，不属本 case）。

**目的（被测契约）**：验证 access-trust 机制的 **bearer 不匹配判定路径**。被测端点/规则：`GET /v1/models`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listModels`，securityScheme `BearerAuth`）；
入口 [`_auth()`](../../../../src/http_api/app.py)（默认 role=`data`）先经 [`unauthenticated_principal()`](../../../../src/http_api/auth.py) 判空，因 `Authorization` 头存在而返回 `None`，再落入 [`authenticate()`](../../../../src/http_api/auth.py)，以 `hmac.compare_digest(supplied, configured)` 比较（`auth.py:56-57`），不匹配则抛 `ApiError(403, "permission_denied")`。
**角色澄清**：§3.2 把本 Case 角色记为 `data`（`/v1/models` 的默认 role），实际观测点是"错误 bearer 被拒"，与是否具备 data 权限无关。设计验证项 `VRC-API-002`；机制 `T-TRUST-BEARER`（机制需求 `R-TRUST-01`：错误凭据→403，见 [access-trust 机制 §5.1/§8 INV-2](../../../20_system_design/mechanisms/access-trust.md)）；
错误信封 `{error:{message,type,code,param,retryable}}`（[errors.py](../../../../src/http_api/errors.py)）。

  > **契约一致性登记（openapi gap）**：openapi `listModels` 的 responses **仅有 `200` 与 `401`**，**未声明 `403`**；本 case 依赖的 403 `permission_denied` 由机制 `T-TRUST-BEARER`（`R-TRUST-01`：错误凭据→403）与实现 [`auth.py`](../../../../src/http_api/auth.py) 保障，属机器契约未表达的路径。本 case 的 Oracle 仍为 403，并把该 openapi 缺口**登记**为已知差异；`X-Request-ID` 亦仅在 openapi 声明的 200 响应头中出现、**非契约**。
**不证明什么**：不证明 **空 bearer** 被拒（ST-AUTH-006）、**无 Authorization 头**的 LAN trust 免登录（ST-AUTH-001）、**data token 访问 admin 面**被拒（ST-AUTH-003）、**管理面未授权优先于资源存在性**（ST-AUTH-009）、**未配置鉴权→503**（ST-AUTH-007）、**缺/非法凭据→401**（ST-AUTH-010）；也不证明 `hmac.compare_digest` 的恒定时间性（INV-2 需专门时序测量，不属本 case）。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `data`（§3.2；wire 契约=错误 bearer 被拒），只读；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；本 case **不复用** `api_client`（其已注入 `Authorization: Bearer dev-data`，会走**正确凭据**路径而得到 200），使用独立 `httpx.Client`（无默认头）并显式设置错误 bearer；初始状态=§2.3 A 类基线（3 provider / 4 deployment / 7 fixed tier）。

## 3. 输入构造

- **输入与构造**：固定请求（无请求体、无查询参数）：
  ```http
  GET /v1/models HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer bogus-token-xxx
  Accept: application/json
  ```
  构造点：`Authorization` 头**必须存在且以 `Bearer ` 开头**（进入 `authenticate()` 的 Bearer 分支），token 值故意不匹配任何已配置凭据（`bogus-token-xxx`）。错误 bearer 的取值不要求特定字面量，只要不等于 `dev-data`/`dev-admin`；不得使用空串（属 ST-AUTH-006）、不得缺省（属 ST-AUTH-001）。源地址为执行机（`192.168.x.x`）到 m5air 可达的 LAN IP。不注入故障；不构造非法输入。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. 建立独立客户端：`httpx.Client(base_url="http://192.168.1.9:8181", timeout=10.0)`，**不设默认 `Authorization`**。
  3. `resp = client.get("/v1/models", headers={"Authorization": "Bearer bogus-token-xxx"})`；记录 status、headers、body。
  4. 断言 `resp.status_code == 403`（凭据不匹配 ⇒ 403；**不是** 401，401 仅用于缺 Bearer 前缀/未命中免登录，属 ST-AUTH-010）。
  5. 解析 body 的 `error` 信封，断言 `error.code == "permission_denied"`、`error.type == "request_error"`、`error.param is None`、`error.retryable is False`，且 `error` 恰含 5 个键（`message/type/code/param/retryable`）。
  6. 断言 body **不含** `object=="list"`/`data` 等 `ModelList` 字段（错误路径不得泄露模型清单）。

**重点关注步骤**：① **错误 bearer ≠ 缺凭据**——403 `permission_denied` 与 401 `authentication_required` 是两条分支，断言错把 401 当成功即 FAIL；② **误用带凭据 fixture**——`api_client` 发送 `dev-data` 会得到 200，令本 case 失去意义，必须用独立无默认头客户端；
③ **空 bearer 与错误 bearer 的区分**——`Bearer `（空串）走 `compare_digest("", …)` 属 ST-AUTH-006，本 case 的 token 非空；④ **信封恰 5 键**——不得把 `category` 当键（本实现无该键，`type` 即类别）；
⑤ **403 在 dispatch 之前**——认证失败不得触达 `app.models.list()`、不产生任何账本义务（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；
⑥ 不在此 case 断言 401/404 或角色隔离。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = access-trust 的凭据判定规则本身——"`Authorization: Bearer <非配置值>` ⇒ 凭据不匹配 ⇒ 403 `permission_denied`"，与 m5air 具体数据无关。
  - HTTP：`403`；响应头 `X-Request-ID` **非契约**（openapi `listModels` 仅声明 `200` 的响应头，且 `403` 未在 responses 中列出——见"契约一致性登记"，`X-Request-ID` 为运行时注入、不列入 Oracle）。
  - body：`{"error":{"message":<str>,"type":"request_error","code":"permission_denied","param":null,"retryable":false}}`，恰 5 键。
  - 无 `ModelList`/业务载荷：本 case 不应出现 `object=="list"` 或 `data`。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==403` 且 `error.code=="permission_denied"` 且 `error.type=="request_error"` 且信封恰 5 键。
  - **FAIL**：返回 200/401/其它 status，或 `error.code` 不符（如落为 `authentication_required`），或信封缺/多键；须给预期 vs 实际与 `reproduction_cmd`。
  - **BLOCKED**：测试代码/契约本身问题（如客户端把错误 bearer 换成 dev-data、断言不可实现）——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或以**空/缺** Authorization 冒充本 case——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：Case 已定义但本轮未执行（例如 suite 因 §2.1 失败整班 skip）。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——本 case 为只读 `GET`，无状态，不创建/修改/删除资源、不写 usage/账本。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存独立请求的原始命令、发送 headers 快照（证明 bearer 存在且错误）、HTTP status/headers/body、执行机 LAN IP、exit code、`elapsed`、环境快照（`/healthz`/`/readyz`）；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；独立 `httpx` 无默认头客户端（不复用 `api_client`）；m5air 已配置 dev-data/dev-admin 凭据；自动化入口 [`ST-AUTH-002.py`](../../../../tests/system/cases/ST-AUTH-002.py)。**不依赖**其它 Case；与 ST-AUTH-001/ST-AUTH-003/ST-AUTH-006/ST-AUTH-010 共享同一鉴权机制但各自独立执行、互不关闭。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
