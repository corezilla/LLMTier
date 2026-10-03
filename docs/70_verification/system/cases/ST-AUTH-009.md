<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-AUTH-009 — 管理面未授权优先于资源存在性

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-AUTH-009` |
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
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/cases/ST-AUTH-009.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`ST-AUTH-009`）；责任摘要、分类与优先级以 [系统测试方案 §6 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单) 清单行为准。
- **测试脚本的唯一依据**：编码者按本文档写测试代码，不需要回读方案或设计正文猜测意图。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-AUTH-009` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-AUTH-009` / 系统设计 §8 认证与授权跨切面（角色/LAN trust/无鉴权） / `VRC-API-002` / `security` / `P1`
- **测试方法（§2.2 方法表行）**：鉴权/授权/脱敏冒烟 + 角色隔离
- 方案清单登记：`ST-AUTH-009`（与 计划 §3 权威清单一致；本文件名 `st-auth-009.md`，唯一对应）。
- 要测什么（责任展开）：`GET /v1/providers/{id}` 在**携带有效 data token**时，**无论 `{id}` 是否存在**都先返回 403 + `permission_denied`，不泄露 `not_found`（授权先于资源存在性）。
- 明确不测什么 / 失败含义：不证明 **admin 凭据下不存在的 provider→404 `not_found`**（ST-PROV-004）、**data token 访问 provider 列表**被拒（ST-AUTH-003）、**别名命名空间**需 admin（ST-AUTH-008）、**错误 bearer** 被拒（ST-AUTH-002）、**缺/非法凭据→401**（ST-AUTH-010）、**未配置鉴权→503**（ST-AUTH-007）。本 case **只**断言认证拒绝发生在资源存在性判定之前、且拒绝形态不因存在性而异。

  > **实现状态（Implemented）**：自动化入口 `ST-AUTH-009.py` 已实现，见 §7。

**目的（被测契约）**：验证 access-trust 的 **INV-3：401/403 不泄露资源存在性**。被测端点/规则：`GET /v1/providers/{id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `getProvider`，securityScheme `AdminBearerAuth`）；
[`app.py`](../../../../src/http_api/app.py) 在解析 `{id}` 后**先**执行 `principal = self._auth("admin")`（`app.py:248`），**再**进入 provider 详情分支与 `app.registry.get_provider(rid)`（`app.py:287-295`）。
data token（`dev-data`）对 `admin` role 不匹配 ⇒ [`authenticate()`](../../../../src/http_api/auth.py) 抛 403 `permission_denied`，**在 `get_provider()` 之前**完成，因此不存在的 `{id}` 也只得到 403、绝不得到 404 `not_found`。
设计验证项 `VRC-API-002`；机制 `T-TRUST-LEAK`（机制需求 `R-TRUST-01`/`R-TRUST-02`；见 [access-trust 机制 §4.4/§8 INV-3/§11](../../../20_system_design/mechanisms/access-trust.md)）；
错误信封 `{error:{message,type,code,param,retryable}}`。**不证明什么**：不证明 **admin 凭据下不存在的 provider→404 `not_found`**（ST-PROV-004）、**data token 访问 provider 列表**被拒（ST-AUTH-003）、**别名命名空间**需 admin（ST-AUTH-008）、**错误 bearer** 被拒（ST-AUTH-002）、**缺/非法凭据→401**（ST-AUTH-010）、**未配置鉴权→503**（ST-AUTH-007）。
本 case **只**断言认证拒绝发生在资源存在性判定之前、且拒绝形态不因存在性而异。

  > **实现状态（Implemented）**：自动化入口 `ST-AUTH-009.py` 已实现，见 §7。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `data`（方案 §6 清单行）；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=计划 §3 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；就绪检查含 计划 §3 必需 provider 已注册（供"存在 id"对照）。本 case 使用独立 `httpx.Client`（无默认头）并显式设置 `Authorization: Bearer dev-data`（或复用 `api_client`）；**不得**使用 `admin_client`；初始状态=§2.3 A 类基线（含 `provider_local`）。

## 3. 输入构造

- **输入与构造**：两组固定请求（无请求体、无查询参数）：
  ```http
  GET /v1/providers/provider_local HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  ```
  ```http
  GET /v1/providers/provider_does_not_exist_auth09 HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  ```
  构造点：**存在 id** = m5air 基线 `provider_local`（计划 §3 保证注册）；**不存在 id** = 明确未注册的字面量 `provider_does_not_exist_auth09`（不得使用真实 prefix 冒充，避免歧义）。两者都携带 **data 凭据** `dev-data`。二者响应必须同为 403 `permission_denied`——存在性差异不得体现在 status/code/body。不注入故障；不构造非法输入。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 计划 §2 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. 建立独立客户端：`httpx.Client(base_url="http://192.168.1.9:8181", timeout=10.0)`，`headers={"Authorization": "Bearer dev-data"}`。
  3. `r_exist = client.get("/v1/providers/provider_local")`；`r_missing = client.get("/v1/providers/provider_does_not_exist_auth09")`；分别记录 status、headers、body。
  4. 断言**两者** `status_code == 403`（授权先于存在性；不存在的 id 也**不**得 404）。
  5. 对两个 body 分别解析 `error` 信封，断言 `error.code == "permission_denied"`、`error.type == "request_error"`、`error.param is None`、`error.retryable is False`，且 `error` 恰含 5 个键。
  6. 断言不存在的 id **不返回** `not_found`/404，且两响应在 status 与 `error.code` 上**无法区分**（无存在性泄露）。
  7. 断言两个 body 均**不含** `ProviderView` 字段（`id`/`name`/`kind`/`secret_ref`）——拒绝路径不得泄露资源内容。

**重点关注步骤**：① **必须用不存在的 id 才能证明"优先"**——若只用存在 id，403 也可以由"handler 内部再次校验"产生，无法排除存在性泄露；本 case 的核心就是 `provider_does_not_exist_auth09` → 403（而非 404）；
② **认证在 `get_provider()` 之前**（`app.py:248` 早于 `app.py:287-295`）——断言应确认没有 registry 查询副作用（无账本义务）；③ **两响应不可区分**——status 与 `code` 必须一致，任何差异即 INV-3 违反；
④ **不能误用 `admin`**——admin 对不存在 id 会得到 404 `not_found`（ST-PROV-004），本 case 的输入必须是 data token；⑤ **不得把 401 当成功**（属 ST-AUTH-010）；
⑥ **信封恰 5 键**（无 `category`）。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = access-trust 的 INV-3 本身——"未授权（admin 面 + data 角色）⇒ 403 `permission_denied`，与目标资源是否存在无关，且响应不泄露存在性"。
  - HTTP：**两者均** `403`；响应头含 `X-Request-ID`。
  - body（两者）：`{"error":{"message":<str>,"type":"request_error","code":"permission_denied","param":null,"retryable":false}}`，恰 5 键。
  - 无 `not_found`：不存在的 id **不得**返回 404 或 `error.code=="not_found"`。
  - 无业务载荷：不出现 `ProviderView` 字段。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：存在 id 与不存在 id **均** `status==403` 且 `error.code=="permission_denied"`，且两条响应在 status/`code` 上不可区分。
  - **FAIL**：任一返回 200/401/404/其它 status，或不存在 id 落为 `not_found`（存在性泄露），或两条响应可区分、信封缺/多键；须给预期 vs 实际与 `reproduction_cmd`。
  - **BLOCKED**：测试代码/契约本身问题（如误用 admin 凭据、不存在 id 构造错、断言不可实现）——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：计划 §3 前置不满足（如 m5air 缺少 `provider_local` 基线）——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或以 admin/错误凭据冒充本 case——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：无（自动化入口已实现；执行状态见 Run 报告）。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——本 case 为只读 `GET`（不存在 id 亦不产生副作用），无状态，不创建/修改/删除资源、不写 usage/账本。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存两条原始命令、发送 headers 快照（证明 `Bearer dev-data`）、两组 HTTP status/headers/body、执行机 LAN IP、exit code、`elapsed`、环境快照（`/healthz`/`/readyz` + provider 列表）；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查（含 计划 §3 `provider_local` 注册）；独立 `httpx` 客户端或 `api_client`（带 `dev-data`）；m5air `GET /v1/providers/{id}` 可用；自动化入口 `tests/system/cases/ST-AUTH-009.py`（已实现）。**不依赖**其它 Case；与 ST-AUTH-003/ST-AUTH-008 共享 admin 面角色隔离，与 ST-PROV-004（admin 正向 not_found）互补但独立执行、互不关闭。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
