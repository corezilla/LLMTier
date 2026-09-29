<!-- STD_DOCUMENT_COVER_BEGIN -->
# ADM-PROV-01 — 列出 providers

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ADM-PROV-01` |
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
| Canonical Path | `docs/70_verification/specifications/cases/adm-prov-01.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ADM-PROV-01` / 系统设计 §8 Provider CRUD 接口（/v1/providers） / `VRC-MGMT-001` / `normal` / `P0`
- 方案清单登记：`ADM-PROV-01`（与 §3.2 权威清单一致；本文件名 `adm-prov-01.md`，唯一对应）。
- 要测什么（责任展开）：`GET /v1/providers` 列出 provider 分页页：HTTP 200 + `ProviderPage`（`data[]` 含 m5air 已知核心 provider，`page.has_more` 为 JSON 布尔）。
- 明确不测什么 / 失败含义：不证明 创建/详情/更新/删除（ADM-PROV-02..13）、不证明 `kind`/`secret_ref` 校验（ADM-PROV-11/12）、不证明响应不含 secret 的强断言（ADM-PROV-14）、不证明分页 `limit=1` cursor 推进（本 case 只观察 `has_more` 布尔，不强求翻页）；不证明 data/admin 角色隔离（AUTH-03/08）。

**目的（被测契约）**：验证 Management Provider CRUD 的**列表读契约**。被测端点/规则：`GET /v1/providers`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listProviders`，`security=AdminBearerAuth`），认证角色 `admin`；成功返回 `ProviderPage`（`data: ProviderView[]`，`page: AdminPageMeta{has_more:boolean, next_cursor:string|null}`，`additionalProperties:false`）；失败走统一错误信封 `{error:{message,type,code,param,retryable}}`（401 `authentication_required` / 403 `permission_denied`）。列表按 `name,id` 排序，允许 `cursor`/`limit` 查询参数（默认 `limit=100`，`_int_param`）。设计验证项 `VRC-MGMT-001`；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`T-CFG-CAS`、`CT-ADMIN-001`（[系统测试方案 §3 覆盖分母与 Case 清单](../../schemes/llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）。**不证明什么**：不证明创建/详情/更新/删除（ADM-PROV-02..13）、不证明 `kind`/`secret_ref` 校验（ADM-PROV-11/12）、不证明响应不含 secret 的强断言（ADM-PROV-14）、不证明分页 `limit=1` cursor 推进（本 case 只观察 `has_more` 布尔，不强求翻页）；不证明 data/admin 角色隔离（AUTH-03/08）。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例；角色 `admin`，只读；见[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）。执行前必须通过[系统测试计划 §3 执行前检](../../plans/llmtier-system-test-plan.md#3-执行前检go--no-go)(../../schemes/llmtier-system-test-scheme.md) 的 6 项就绪检查（详见 §2.1）；任一失败 → 整班 BLOCKED/SKIP，不得改用模拟路径。fixture（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）：`admin_client`。初始状态：m5air 现有 3 provider / 4 deployment / 7 fixed tier，其中 `provider_minimax`/`provider_local`/`provider_omlx_m5mac` 必在（§2.1.6）。**注意**：m5air 经多轮人工/历史测试后 provider 可能多于 3 个，故本 case **只断言包含关系**，不断言总数。

## 3. 输入构造

- **输入与构造**：固定请求（无请求体；本 case 不带 `cursor`/`limit`，走默认分页）：
  ```http
  GET /v1/providers HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：`Authorization: Bearer dev-admin` 固定 admin 角色；无 body（GET）；不注入故障；不构造非法输入（非法/缺凭据属 AUTH-*）。`page.has_more`/`next_cursor` 的**值不固定**（取决于 provider 总数与 `limit=100`），只断言类型与结构。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = admin_client.get("/v1/providers")`；记录 status、`Content-Type`、原始 body。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`。
  4. 解析 body：断言 `data` 为数组、`page` 为对象；断言 `page` 键集恰为 `{has_more, next_cursor}`（`additionalProperties:false`）。
  5. 断言 `isinstance(page["has_more"], bool)`；`next_cursor` 为字符串或 `null`。
  6. 计算 `ids = {p["id"] for p in data}`，断言核心集合 `{provider_minimax, provider_local, provider_omlx_m5mac}` ⊆ `ids`；抽查每个 `ProviderView` 必填键 `{id,name,kind,endpoint,has_secret,enabled,usage,request_usage,version}` 齐备。

**重点关注步骤**：① **`page` 是嵌套对象**——不是顶层 `has_more`；读错层级即漏判；② **`has_more` 类型**——必须是 JSON 布尔，不能是 `0/1`/字符串；③ **包含而非相等**——m5air provider 集合会随历史变化，本 case 只断言 3 个核心必在、不硬编码总数；④ **不得把错误信封当列表**——非 200 需先确认是可解释的 `ERR-AUTH-*`，而非把 `{error:...}` 当 `data` 读；⑤ **服务端读路径副作用**——[`admin.page()`](../../../../src/management/admin.py) 每次列表调用会在 M007 `query_snapshots`/`query_snapshot_items` 落一条 10 分钟 TTL 的分页快照（即使无 `cursor`），这是服务端实现行为、非用户资源；报告须登记该写入，**不得声称"零写入"**；⑥ 本 case 不承担 `secret` 不泄露的强断言（ADM-PROV-14）。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ProviderPage`/`ProviderView`/`AdminPageMeta` wire 形态（不依赖 m5air 具体数量）。
  - HTTP：`200`；`Content-Type: application/json`。
  - body：`data` 为 `ProviderView[]`（元素含全部必填键；`has_secret` 为布尔、`endpoint` 为 URI、`usage` 为 `ProviderUsageProfileView`、`request_usage` 为 `ProviderRequestUsageView`）；`page` 键集恰为 `{has_more,next_cursor}`。
  - 基线：`{provider_minimax, provider_local, provider_omlx_m5mac}` ⊆ `data[].id`。
  - 无错误信封：本 case 不应出现 `{"error":{...}}`。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==200` 且 `data` 合法 `ProviderView[]` 且含 3 个核心 provider 且 `page` 键集恰为 `{has_more,next_cursor}`、`has_more` 为 JSON 布尔。
  - **FAIL**：status 非 200 且存储/鉴权健康，或 body 非合法 `ProviderPage`（缺 `page`/键集不符/`has_more` 非布尔/核心 provider 缺失）。
  - **BLOCKED**：测试代码/契约本身问题（如 fixture 写不出、断言逻辑错、语义不清）——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足（m5air 不可达、`/readyz` 非 7 tier、双 OMLX 离线、核心 provider 未注册）——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`；不得以未跑冒充 PASS。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需资源 teardown**——本 case 不改 provider/deployment/service-level、不写注入。第/各步列表 GET 的服务端 `query_snapshots` 分页快照（10 分钟 TTL）由服务端自身产生，A 类不手工删除系统表行，等待过期即可；B 类整班 `rm -rf` 临时目录时随库消失。 退出前确认 `/readyz` 仍显示 7 tier、provider 列表未变、无未清空注入项。若被误跑于 B 类临时实例，则按[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md) 整班 `stop()` + `rm -rf` 临时目录。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[系统测试计划 §6 证据与 Run 记录规则](../../plans/llmtier-system-test-plan.md#6-证据与-run-记录规则)(../../schemes/llmtier-system-test-scheme.md)：Run ID=`<date>/A-api`；保存原始 status/headers/body（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。

- **依赖**：[系统测试计划 §3 执行前检](../../plans/llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查（含 §2.1.6 必需 provider/deployment）；`admin_client` fixture（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）；`ProviderPage` 机器契约（`interfaces/openapi/llmtier.openapi.json`）；自动化入口 [`at_adm_prov_01.py`](../../../../tests/system/api_test_v03/at_adm_prov_01.py)。**不依赖**其它 Case；与 ADM-PROV-03/14 共享列表/详情读路径但各自独立执行。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
