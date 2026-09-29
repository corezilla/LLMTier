<!-- STD_DOCUMENT_COVER_BEGIN -->
# AUTH-03 — Data token 访问 admin 面

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `AUTH-03` |
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
| Canonical Path | `docs/70_verification/specifications/cases/auth-03.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`AUTH-03` / 系统设计 §8 认证与授权跨切面（角色/LAN trust/无鉴权） / `VRC-API-002` / `security` / `P0`
- 方案清单登记：`AUTH-03`（与 §3.2 权威清单一致；本文件名 `auth-03.md`，唯一对应）。
- 要测什么（责任展开）：`GET /v1/providers` 在**携带有效 data token**时被拒，返回 403 + `permission_denied`（data 角色不授权 admin 面）。
- 明确不测什么 / 失败含义：不证明 **无 token 的 LAN trust** 是否受理 admin 面（AUTH-04）、**管理面未授权优先于资源存在性**（AUTH-09）、**别名命名空间**需 admin（AUTH-08）、**错误 bearer** 被拒（AUTH-02）、**缺/非法凭据→401**（AUTH-10）、**未配置鉴权→503**（AUTH-07）；也不证明 `permission_denied` 的具体比较是否恒定时间（INV-2）。

**目的（被测契约）**：验证 access-trust 机制的 **per-endpoint 角色选择与角色隔离**。被测端点/规则：`GET /v1/providers`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listProviders`，securityScheme `AdminBearerAuth`）；[`app.py`](../../../../src/http_api/app.py) 在路由分派前先执行 `principal = self._auth("admin")`（`app.py:239`），即 [`authenticate()`](../../../../src/http_api/auth.py) 以 role=`admin` 取 `_configured_token("admin")`（= `dev-admin`），而请求携带的是 data token（`dev-data`），`hmac.compare_digest` 不匹配 ⇒ 403 `permission_denied`（`auth.py:56-57`）。设计验证项 `VRC-API-002`；机制 `T-TRUST-SHARED`、`T-TRUST-ENDPOINTS`（机制需求 `R-TRUST-02`：按端点选 role、分发；见 [access-trust 机制 §5.1/§8 INV-4](../../../20_system_design/mechanisms/access-trust.md)）；错误信封 `{error:{message,type,code,param,retryable}}`。**不证明什么**：不证明 **无 token 的 LAN trust** 是否受理 admin 面（AUTH-04）、**管理面未授权优先于资源存在性**（AUTH-09）、**别名命名空间**需 admin（AUTH-08）、**错误 bearer** 被拒（AUTH-02）、**缺/非法凭据→401**（AUTH-10）、**未配置鉴权→503**（AUTH-07）；也不证明 `permission_denied` 的具体比较是否恒定时间（INV-2）。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `data`（§3.2）；见[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；本 case **使用** `api_client` fixture（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)），其 `Authorization: Bearer dev-data` 正是被测输入；**不得**改用 `admin_client`（会以 `dev-admin` 通过，令本 case 失去意义）；初始状态=§2.3 A 类基线（3 provider / 4 deployment / 7 fixed tier）。

## 3. 输入构造

- **输入与构造**：固定请求（无请求体、无查询参数）：
  ```http
  GET /v1/providers HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Accept: application/json
  ```
  构造点：使用 m5air 已配置的 **data 凭据** `dev-data`（`api_client` 默认头），访问 **admin 端点** `/v1/providers`。`dev-data` 是合法凭据，但角色为 `data`，与端点要求的 `admin` 不匹配。不注入故障；不构造非法输入。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = api_client.get("/v1/providers")`（fixture 已带 `Authorization: Bearer dev-data`）；记录 status、headers、body。
  3. 断言 `resp.status_code == 403`（data token 不满足 admin 角色 ⇒ 403；不是 200、不是 401）。
  4. 解析 body 的 `error` 信封，断言 `error.code == "permission_denied"`、`error.type == "request_error"`、`error.param is None`、`error.retryable is False`，且 `error` 恰含 5 个键。
  5. 断言 body **不含** `data`/`has_more` 等 `ProviderPage` 字段（拒绝路径不得泄露 provider 列表）。
  6. （可选交叉核对）用 `admin_client.get("/v1/providers")` 发一次并记录 200，佐证"同一端点、凭据角色不同结果不同"——该次通过不由本 case 断言（属 AUTH-04/ADM-PROV-01 语义）。

**重点关注步骤**：① **合法凭据 + 错误角色 ≠ 无权限**——`dev-data` 能过 data 面（AUTH-01/DP-MODELS），但在 admin 面必须 403；② **不能误用 `admin_client`**——那会发送 `dev-admin` 而 200，本 case 的输入必须是 data token；③ **`_auth("admin")` 在路由分发前**（`app.py:239`）——403 先于 `list_providers()`，无上游调用、无账本义务；④ **不得把 401 当成功**——凭据形态合法但无权是 403，401 属 AUTH-10；⑤ **信封恰 5 键**（无 `category` 键，`type` 即类别）；⑥ 不在此 case 断言资源存在性优先级（AUTH-09）。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = access-trust 的角色矩阵本身——"data 角色凭据访问 admin 端点 ⇒ 403 `permission_denied`"，与 m5air 具体 provider 数据无关。
  - HTTP：`403`；响应头含 `X-Request-ID`。
  - body：`{"error":{"message":<str>,"type":"request_error","code":"permission_denied","param":null,"retryable":false}}`，恰 5 键。
  - 无业务载荷：本 case 不应出现 `ProviderPage` 的 `data`/`has_more`。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==403` 且 `error.code=="permission_denied"` 且 `error.type=="request_error"` 且信封恰 5 键。
  - **FAIL**：返回 200（角色隔离失效）/401/其它 status，或 `error.code` 不符、信封缺/多键；须给预期 vs 实际与 `reproduction_cmd`。
  - **BLOCKED**：测试代码/契约本身问题（如误用 admin 凭据、断言不可实现）——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足（如 m5air 未配置 dev-data）——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或以 admin/错误凭据冒充本 case——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：Case 已定义但本轮未执行（例如 suite 因 §2.1 失败整班 skip）。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——本 case 为只读 `GET`，无状态，不创建/修改/删除资源、不写 usage/账本。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存原始命令、发送 headers 快照（证明为 `Bearer dev-data`）、HTTP status/headers/body、执行机 LAN IP、exit code、`elapsed`、环境快照（`/healthz`/`/readyz`）；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../../plans/llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../../plans/llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；`api_client` fixture（带 `dev-data`，[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）；m5air admin 端点 `/v1/providers` 可用；自动化入口 [`at_auth_03.py`](../../../../tests/system/api_test_v03/at_auth_03.py)。**不依赖**其它 Case；与 AUTH-04/AUTH-08/AUTH-09 共享 admin 面鉴权但各自独立执行、互不关闭。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
