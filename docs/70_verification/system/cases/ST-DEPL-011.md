<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-DEPL-011 — 更新 deployment data token 403

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-DEPL-011` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-DEPL-011.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-DEPL-011` / 系统设计 §8 Deployment CRUD 接口（/v1/deployments/dep_local_gemma） / `VRC-MGMT-002` / negative / P1（[方案清单 `ST-DEPL-011`](../llmtier-system-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：鉴权/角色隔离冒烟（data→admin 面 403）+ 错误猜测 + 反例驱动

- 要测什么（责任展开）：`PATCH /v1/deployments/dep_local_gemma` 携带**有效 data token** 时被拒，返回 403 + `permission_denied`（data 角色不授权管理写面）；拒绝发生在任何 body 解析/资源变更之前，**零副作用**。

- 明确不测什么 / 失败含义：不证明无 token 的 LAN trust（ST-AUTH-004）、错误 bearer（ST-AUTH-002）、缺/非法凭据 401（ST-AUTH-010）、未配置鉴权 503（ST-AUTH-007）；不证明该写路由的**成功**语义（其正向 Case）；不证明 `permission_denied` 比较是否恒定时间（INV-2）。失败含义＝管理写面的角色门可被 data 凭据绕过。

**目的（被测契约）**：验证 access-trust 机制的**管理写面逐路由角色门**。被测端点/规则：`PATCH /v1/deployments/dep_local_gemma`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json)）；
入口 [`app.py`](../../../../src/http_api/app.py) 在 provider/deployment/service-level 路由块前先执行 `principal = self._auth("admin")`（`app.py:248`），data token 与 admin token `hmac.compare_digest` 不匹配 ⇒ 403 `permission_denied`（[`auth.py`](../../../../src/http_api/auth.py):56-57）。
设计验证项 `VRC-MGMT-002`；机制 `T-TRUST-SHARED`、`T-TRUST-ENDPOINTS`。**不证明什么**：不证明 LAN trust/错误 bearer/401/503；不证明成功语义；不证明恒定时间。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `data`）。前置 = §2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；本 case **使用** `api_client` fixture（其 `Authorization: Bearer dev-data` 即被测输入），**不得**改用 `admin_client`（会以 `dev-admin` 通过，令本 case 失去意义）；初始状态 = §2.3 A 类基线（3 provider / 4 deployment / 7 fixed tier）。本 case 为拒绝路径，**零副作用**。
- **被测入口**：

  ```http
  PATCH /v1/deployments/dep_local_gemma HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-data
  Content-Type: application/json
  ```

## 3. 输入构造

- **输入与构造**：固定请求：
  ```json
  {"name": "x"}
  ```
  构造点：使用 m5air 已配置的 **data 凭据** `dev-data`（`api_client` 默认头），访问**管理写端点**。`dev-data` 合法但角色为 `data`，与端点要求的 `admin` 不匹配；角色门在 body 解析前触发，故 body 形态不影响判定。不注入故障。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = api_client.patch("/v1/deployments/dep_local_gemma", json={"name": "x"})`；记录 status、headers、body。
  3. 断言 `resp.status_code == 403`（data token 不满足 admin 角色；不是 200/201/204、不是 401）。
  4. 解析 body 的 `error` 信封，断言 `error.code == "permission_denied"`、`error.type == "request_error"`、`error.param is None`、`error.retryable is False`，且恰含 5 个键。
  5. （可选交叉核对）以 `admin_client` 发同一请求并记录其（成功/校验）状态，佐证"同端点、凭据角色不同结果不同"——该次不由本 case 断言。

**重点关注步骤**：① **合法凭据 + 错误角色 ≠ 无权限**——`dev-data` 能过 data 面，但在管理写面必须 403；② **不能误用 `admin_client`**；③ **403 先于 body 解析与资源变更**（`app.py:248` 在路由块前）——零上游、零账本、零资源变更；④ **不得把 401 当成功**（401 属 ST-AUTH-010）；⑤ **信封恰 5 键**；⑥ **`method` 与路径逐字匹配**。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = access-trust 的角色矩阵本身——"data 角色凭据访问 admin 写端点 ⇒ 403 `permission_denied`"。
  - HTTP `403`；响应头含 `X-Request-ID`。
  - body：`{"error":{"message":<str>,"type":"request_error","code":"permission_denied","param":null,"retryable":false}}`，恰 5 键。
  - 无业务载荷；无资源变更。
- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==403` 且 `error.code=="permission_denied"` 且 `error.type=="request_error"` 且信封恰 5 键。
  - **FAIL**：返回 200/201/204/401/其它 status，或 code/信封不符；须给预期 vs 实际与 `reproduction_cmd`。
  - **BLOCKED**：测试代码/契约本身问题（如误用 admin 凭据）。
  - **SKIP**：§2.1 前置不满足。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径，或以 admin/错误凭据冒充。
  - **NOT_RUN**：有实现但本轮未执行。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——角色门在写之前拒绝，无状态变更、无资源创建/修改/删除、无账本义务。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。若被误跑于 B 类实例则整班 `stop()` + `rm -rf`。

## 7. 自动化位置与状态

- **测试文件 / 测试函数**：`tests/system/cases/ST-DEPL-011.py`（**Implemented**）。
- **单 Case 执行命令**：`PYTHONPATH=src python3 -m pytest tests/system/cases/ST-DEPL-011.py -q`。
- **实现状态**：Implemented；执行与 Verdict 归 Run 报告。

**证据与 Run**：保存原始命令、发送 headers 快照（证明为 `Bearer dev-data`）、HTTP status/headers/body、执行机 LAN IP、exit code、`elapsed`、环境快照（`/healthz`/`/readyz`）；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（本 case `environment:"a"`）。

**依赖**：就绪检查；`api_client` fixture（带 `dev-data`）；m5air 管理写端点 `PATCH /v1/deployments/dep_local_gemma` 可用；自动化入口 `ST-DEPL-011.py`。**不依赖**其它 Case；与 ST-AUTH-003（读面 403）及本组其它写面 403 各自独立执行。

