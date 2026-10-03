<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-LOGS-003 — 日志接口 data token 403

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-LOGS-003` |
| Document Version | `0.1.0-draft.3` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-30` |
| Last Modified Date | `2026-10-03` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/cases/ST-LOGS-003.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-LOGS-003` / 系统设计 §8 日志接口（GET /v1/logs） / `VRC-LOG-001` / negative / P1（[方案清单 `ST-LOGS-003`](../llmtier-system-test-scheme.md)）。
- **测试方法（§2.2 方法表行）**：鉴权/角色隔离冒烟（data→admin 面 403）+ 错误猜测 + 反例驱动

- 要测什么（责任展开）：`GET /v1/logs` 携带**有效 data token** 时被拒，返回 403 + `permission_denied`（data 角色不授权观测/管理读面）。

- 明确不测什么 / 失败含义：不证明无 token 的 LAN trust（ST-AUTH-004）、错误 bearer（ST-AUTH-002）、缺/非法凭据 401（ST-AUTH-010）、未配置鉴权 503（ST-AUTH-007）；不证明该端点的**成功**读语义（其正向 Case）或 400 校验（缺窗/非法分页）；不证明脱敏（ST-AUDIT-001/ST-LOGS-001）。失败含义＝观测读面角色门可被 data 凭据绕过。

**目的（被测契约）**：验证 access-trust 机制对**观测/管理读面**的角色隔离。被测端点/规则：`GET /v1/logs`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json)）；入口 [`app.py`](../../../../src/http_api/app.py) 在观测读路由块前先执行 `principal = self._auth("admin")`（`app.py:248`），data token 不匹配 ⇒ 403 `permission_denied`。设计验证项 `VRC-LOG-001`；机制 `T-TRUST-SHARED`。**不证明什么**：不证明 LAN trust/错误 bearer/401/503；不证明成功读语义/400 校验/脱敏。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `data`）。前置 = 计划 §3 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；本 case **使用** `api_client` fixture（`Bearer dev-data`），**不得**改用 `admin_client`；初始状态 = §2.3 A 类基线。本 case 为只读拒绝路径，**零副作用**。
- **被测入口**：

  ```http
  GET /v1/logs HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Accept: application/json
  ```

## 3. 输入构造

- **输入与构造**：固定请求（查询参数可选，角色门先于参数解析）：
  ```http
  GET /v1/logs HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Accept: application/json
  ```
  构造点：使用 m5air 的 **data 凭据** `dev-data` 访问**管理读端点**；`dev-data` 合法但角色为 `data`。`不传 from/to。`不注入故障。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 计划 §2 基线（由 `pytest_configure` 自动执行）。
  2. `resp = api_client.get("/v1/logs")`；记录 status、headers、body。
  3. 断言 `resp.status_code == 403`（不是 200、不是 401）。
  4. 解析 `error` 信封，断言 `error.code == "permission_denied"`、`error.type == "request_error"`、`error.param is None`、`error.retryable is False`，恰含 5 键。
  5. 断言 body **不含** LogPage 业务字段（拒绝路径不得泄露观测/管理数据）。

**重点关注步骤**：① **合法凭据 + 错误角色 ≠ 无权限**；② **不能误用 `admin_client`**；③ **403 先于参数校验**——即使不传 `from`/`to` 也应 403（角色门在路由块前，`app.py:248`），不得先 400；④ **不得把 401 当成功**；⑤ **信封恰 5 键**；⑥ **不泄露业务载荷**。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = access-trust 角色矩阵——"data 角色凭据访问 admin 读端点 ⇒ 403 `permission_denied`"。
  - HTTP `403`；响应头含 `X-Request-ID`。
  - body：`{"error":{"message":<str>,"type":"request_error","code":"permission_denied","param":null,"retryable":false}}`，恰 5 键。
  - 无 LogPage 业务载荷。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==403` 且 `error.code=="permission_denied"` 且 `error.type=="request_error"` 且信封恰 5 键。
  - **FAIL**：返回 200/401/400/其它 status，或 code/信封不符；须给预期 vs 实际与 `reproduction_cmd`。
  - **BLOCKED**：测试代码/契约本身问题（如误用 admin 凭据）。
  - **SKIP**：计划 §3 前置不满足。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或以 admin/错误凭据冒充。
  - **NOT_RUN**：有实现但本轮未执行。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——本 case 为只读 `GET` 且被拒，无状态变更。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。若被误跑于 B 类实例则整班 `stop()` + `rm -rf`。

## 7. 自动化位置与状态

- **测试文件 / 测试函数**：`tests/system/cases/ST-LOGS-003.py`（Implemented）。
- **单 Case 执行命令**：`PYTHONPATH=src python3 -m pytest tests/system/cases/ST-LOGS-003.py -q`。
- **实现状态**：Implemented；执行与 Verdict 归 Run 报告。

**证据与 Run**：保存原始命令、发送 headers 快照（证明为 `Bearer dev-data`）、HTTP status/headers/body、执行机 LAN IP、exit code、`elapsed`、环境快照（`/healthz`/`/readyz`）；落位见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（本 case `environment:"a"`）。

**依赖**：就绪检查；`api_client` fixture（带 `dev-data`）；m5air `GET /v1/logs` 可用；自动化入口 `ST-LOGS-003.py`。**不依赖**其它 Case；与 ST-AUTH-003 及本组其它读面 403 各自独立执行。

