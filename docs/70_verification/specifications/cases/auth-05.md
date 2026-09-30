<!-- STD_DOCUMENT_COVER_BEGIN -->
# AUTH-05 — 公共端点无需 token

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `AUTH-05` |
| Document Version | `0.1.0-draft.2` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-29` |
| Last Modified Date | `2026-09-29` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/specifications/cases/auth-05.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`AUTH-05`）；责任摘要、分类与优先级以 [系统测试方案 §3 覆盖分母与 Case 清单](../../schemes/llmtier-system-test-scheme.md#3-覆盖分母与-case-清单) 清单行为准。
- **测试脚本的唯一依据**：编码者按本文档写测试代码，不需要回读方案或设计正文猜测意图。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `AUTH-05` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`AUTH-05` / 系统设计 §8 认证与授权跨切面（角色/LAN trust/无鉴权） / `VRC-API-002` / `security` / `P0`
- 方案清单登记：`AUTH-05`（与 §3.2 权威清单一致；本文件名 `auth-05.md`，唯一对应）。
- 要测什么（责任展开）：`GET /healthz` 在**不带任何凭据、任意来源**下被受理，返回 200 + `status="ok"`（公共存活端点不进入鉴权路径）。
- 明确不测什么 / 失败含义：不证明 `/readyz` 的就绪语义（HEALTH-02/03/04/05）、不证明任何受保护端点（`/v1/*`）的鉴权（AUTH-01/02/03/04/06/07/08/09/10）、不证明 LAN trust 免登录（AUTH-01/04）、不证明未配置鉴权时受保护端点的 503（AUTH-07）。本 case **不断言** `/healthz` 不受 bootstrap 失败影响之外的 `/readyz` 行为。

**目的（被测契约）**：验证公开存活端点的 **no-auth 契约**。被测端点/规则：`GET /healthz`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `healthz`，无 securityScheme）；[`app.py`](../../../../src/http_api/app.py) 在 `_dispatch()` 最前段直接返回 `self._json(200, health_view(__version__))`（`app.py:196`），**不调用** `self._auth()`/`_auth("admin")`/`_auth_either()`，也不等待 bootstrap；因此 `/healthz` 不受凭据角色、LAN trust、`_configured_token` 或 bootstrap 状态影响。设计验证项 `VRC-API-002`；机制 `T-TRUST-NOCFG`、`T-TRUST-SHARED`（机制需求 `R-TRUST-04`；见 [access-trust 机制 §5.1/§12.2](../../../20_system_design/mechanisms/access-trust.md)）。**不证明什么**：不证明 `/readyz` 的就绪语义（HEALTH-02/03/04/05）、不证明任何受保护端点（`/v1/*`）的鉴权（AUTH-01/02/03/04/06/07/08/09/10）、不证明 LAN trust 免登录（AUTH-01/04）、不证明未配置鉴权时受保护端点的 503（AUTH-07）。本 case **不断言** `/healthz` 不受 bootstrap 失败影响之外的 `/readyz` 行为。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `none`（§3.2）；见[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；本 case 使用独立 `httpx.Client`（无默认头）；`/healthz` 在源码中先于 `app.bootstrap_error` 判空，故本 case 亦可在 bootstrap 异常实例上通过，但 A 类就绪检查已排除该场景；初始状态=§2.3 A 类基线（3 provider / 4 deployment / 7 fixed tier）。

## 3. 输入构造

- **输入与构造**：固定请求（无请求体、无查询参数、无凭据）：
  ```http
  GET /healthz HTTP/1.1
  Host: 192.168.1.9:8181
  Accept: application/json
  ```
  构造点：**不发送任何 `Authorization` 头**（既不是空串也不是 `Bearer `）；不设 `X-Principal-ID`。来源地址不参与判定（本 case 不依赖 LAN trust）。不注入故障；不构造非法输入。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. 建立独立客户端：`httpx.Client(base_url="http://192.168.1.9:8181", timeout=10.0)`，**不设 `Authorization`**。
  3. `resp = client.get("/healthz")`；记录 status、headers、body。
  4. 断言 `resp.status_code == 200`（公共端点未进入鉴权 ⇒ 未被 401/403/503）。
  5. 解析 body：断言 `body["status"] == "ok"` 且 `isinstance(body["version"], str)`（`health_view` 契约，[`src/http_api/health.py`](../../../../src/http_api/health.py)）。
  6. 断言 body **不含** `{"error":{...}}`（公共存活端点不返回错误信封）。

**重点关注步骤**：① **真正无凭据**——不得用带默认头的 `api_client`/`admin_client`；必须独立无头客户端，否则无法证明"无需 token"；② **`/healthz` ≠ `/readyz`**——本 case 只断言存活；`/readyz` 的就绪/降级/未就绪属 HEALTH-02/03/04/05，不可混入；③ **`/healthz` 不调用 `_auth*`**——断言前应在源码确认 `app.py:196` 位于所有 `_auth*` 之前，避免把"受信 LAN 恰好免登录"误当"公共端点无需鉴权"（后者在非受信来源也应为 200，但本 case 不构造非受信来源）；④ **body 必为 `health_view`**——只断言 200 不够，须验证 `status="ok"` + `version:str`；⑤ 不在此 case 断言 `/readyz` 或任何受保护端点。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = 公开端点契约本身——"`GET /healthz` 无凭据 ⇒ 200 + `{status:"ok",version:<str>}`"，与来源、凭据、bootstrap 状态无关。
  - HTTP：`200`；响应头 `X-Request-ID` **非契约**（openapi `getHealth` 的 `200` 未声明任何响应头；该头由 [`app.py`](../../../../src/http_api/app.py) 运行时注入，**仅实现行为**，不列入 Oracle）。
  - body：`{"status":"ok","version":<str>, ...}`（`health_view` 字段）。
  - 无错误信封：本 case 不应出现 `{"error":{...}}`。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==200` 且 `body.status=="ok"` 且 `body.version` 为字符串。
  - **FAIL**：返回非 200，或 `status != "ok"`、`version` 非字符串、出现错误信封；须给预期 vs 实际与 `reproduction_cmd`。
  - **BLOCKED**：测试代码/契约本身问题（如误带凭据、断言不可实现）——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足（m5air 不可达）——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或以带凭据请求冒充"无需 token"——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：Case 已定义但本轮未执行（例如 suite 因 §2.1 失败整班 skip）。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——本 case 为只读 `GET`，无状态，不创建/修改/删除资源、不写 usage/账本。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存独立请求的原始命令、发送 headers 快照（证明无 `Authorization`）、HTTP status/headers/body、exit code、`elapsed`、环境快照（`/healthz`/`/readyz`）；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../../plans/llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../../plans/llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；独立 `httpx` 无头客户端；m5air `GET /healthz` 可用；自动化入口 [`at_auth_05.py`](../../../../tests/system/api_test_v03/at_auth_05.py)。**不依赖**其它 Case；与 HEALTH-01 观测同一端点但本 case 只从鉴权视角断言"无需 token"，二者独立执行。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
