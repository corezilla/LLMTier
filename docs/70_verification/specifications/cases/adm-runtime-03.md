<!-- STD_DOCUMENT_COVER_BEGIN -->
# ADM-RUNTIME-03 — 运行时快照缺凭据 401

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ADM-RUNTIME-03` |
| Document Version | `0.1.0-draft.2` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-30` |
| Last Modified Date | `2026-10-01` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/specifications/cases/adm-runtime-03.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ADM-RUNTIME-03` / 系统设计 §8 运行态接口（GET /v1/runtime） / `VRC-API-002` / security / P2（[方案清单 `ADM-RUNTIME-03`](../../schemes/llmtier-system-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：鉴权/授权冒烟（缺/非法凭据 401）

- 要测什么（责任展开）：受保护端点 `GET /v1/runtime` 在**携带非法授权方案**（`Authorization: Basic …`）时返回 401 + `authentication_required`。

- 明确不测什么 / 失败含义：不证明错误 bearer（形态合法）→403（AUTH-02）、空 bearer→403（AUTH-06）、data token 访问 admin 面→403（ADM-RUNTIME-02/AUTH-03）、未配置鉴权→503（AUTH-07）、无 token 的 LAN trust→200（AUTH-04）。本 case **不**证明非受信来源下"缺 Bearer→401"（见构造说明）。失败含义＝运行态读面的凭据形态判定缺失。

**目的（被测契约）**：验证 access-trust 的**缺凭据/非法方案判定路径**在 `/v1/runtime` 上的表现。被测端点/规则：`GET /v1/runtime`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `getRuntime`，`security=AdminBearerAuth`）；入口 [`_auth("admin")`](../../../../src/http_api/app.py) 先经 [`unauthenticated_principal()`](../../../../src/http_api/auth.py)（因 `Authorization` 头存在返回 `None`），再落入 `authenticate()`：`raw.startswith("Bearer ")` 为假 ⇒ 抛 `ApiError(401, "authentication_required")`（`auth.py:53-54`）。设计验证项 `VRC-API-002`；机制 `T-TRUST-BEARER`。**构造诚实性**：A/B 两班均**无法构造"完全无头"的 401**（源码对 loopback/RFC1918 无 `Authorization` 头无条件授权），故以**非法方案**（`Basic`）触发同一 401 分支；不得据此声称已验证"来源不受信"门。**不证明什么**：不证明 403/503/LAN trust/恒定时间。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `none`）。前置 = §2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；本 case **不复用** `api_client`/`admin_client`（它们注入合法 bearer 会 200），使用独立 `httpx.Client`（无默认头）并显式设置 `Basic` 方案；初始状态 = §2.3 A 类基线。本 case 为只读拒绝路径，**零副作用**。
- **被测入口**：

  ```http
  GET /v1/runtime HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Basic ZGV2LWRhdGE=
  Accept: application/json
  ```

## 3. 输入构造

- **输入与构造**：固定请求（无请求体、无查询参数）：
  ```http
  GET /v1/runtime HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Basic ZGV2LWRhdGE=
  Accept: application/json
  ```
  构造点：`Authorization` 头**存在且非 `Bearer ` 前缀**（`Basic <base64>`，仅作形态占位），落入 `authenticate()` 的"非法方案"分支 ⇒ 401。变体（可选）：`Authorization: Token dev-data` 同样应 401。不得使用 `Bearer <错误值>`（属 AUTH-02）或 `Bearer `（属 AUTH-06）。不注入故障。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行）。
  2. 建立独立客户端：`httpx.Client(base_url="http://192.168.1.9:8181", timeout=10.0)`，**不设默认 `Authorization`**。
  3. `resp = client.get("/v1/runtime", headers={"Authorization": "Basic ZGV2LWRhdGE="})`；记录 status、headers、body。
  4. 断言 `resp.status_code == 401`（**不是** 403，也不是 200）。
  5. 解析 `error` 信封，断言 `error.code == "authentication_required"`、`error.type == "request_error"`、`error.param is None`、`error.retryable is False`，恰含 5 键。
  6. 断言 body **不含** `deployments`/`providers`/`queues` 等运行态快照字段（拒绝路径不得泄露运行态）。
  7. （可选）对变体 `Authorization: Token dev-data` 重复第 3–6 步，确认同样 401。

**重点关注步骤**：① **401 与 403 的分界**——非法方案/缺 Bearer 前缀 ⇒ 401；形态合法但值错 ⇒ 403（AUTH-02/06）；② **不能以"完全无头"构造**——A/B 上无头因 LAN/loopback trust 得 200；③ **不得伪造来源**——代码以 socket `client_address[0]` 判定，`X-Forwarded-For` 不参与，伪造判 INVALID；④ **401 的 `type` 是 `request_error`**，信封恰 5 键；⑤ **拒绝先于 dispatch**——无上游、无账本；⑥ 不泄露运行态。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = access-trust 的凭据形态规则——"受保护端点 + 非 `Bearer` 授权方案 ⇒ 401 `authentication_required`"（来源门未被本构造覆盖）。
  - HTTP `401`；响应头含 `X-Request-ID`。
  - body：`{"error":{"message":<str>,"type":"request_error","code":"authentication_required","param":null,"retryable":false}}`，恰 5 键。
  - 无运行态业务载荷。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==401` 且 `error.code=="authentication_required"` 且 `error.type=="request_error"` 且信封恰 5 键。
  - **FAIL**：返回 200/403/其它 status，或 code/信封不符。
  - **BLOCKED**：若执行者只尝试"完全无头"路径并因 A/B 恒 200 而无法触达 401，判 BLOCKED（构造失败），并说明非受信来源不可得。
  - **SKIP**：§2.1 前置不满足。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充，或以 `X-Forwarded-For`/改 `client_address` 伪造来源，或以错误/空 bearer 冒充。
  - **NOT_RUN**：有实现但本轮未执行。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——本 case 为只读 `GET` 且被拒，无状态变更。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。若被误跑于 B 类实例则整班 `stop()` + `rm -rf`。

## 7. 自动化位置与状态

- **测试文件 / 测试函数**：`tests/system/api_test_v03/at_adm_runtime_03.py`（Implemented）。
- **单 Case 执行命令**：`PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/at_adm_runtime_03.py -q`。
- **实现状态**：Implemented；执行与 Verdict 归 Run 报告。

**证据与 Run**：保存独立请求的原始命令、发送 headers 快照（证明为 `Basic` 方案）、HTTP status/headers/body、执行机 LAN IP、exit code、`elapsed`、环境快照（`/healthz`/`/readyz`）；落位见[系统测试计划 §6 证据与 Run 记录规则](../../plans/llmtier-system-test-plan.md#6-证据与-run-记录规则)（本 case `environment:"a"`）。

**依赖**：就绪检查；独立 `httpx` 无默认头客户端；m5air `GET /v1/runtime` 可用；自动化入口 `at_adm_runtime_03.py`。**不依赖**其它 Case；与 ADM-RUNTIME-02（data token→403）构成"凭据形态→状态码"对照（403/401）。

