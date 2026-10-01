<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-PMOD-002 — 不存在 provider

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-PMOD-002` |
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
| Template Conformance | `native` |
| Tailoring Reference | none |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/cases/ST-PMOD-002.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-PMOD-002`）；责任摘要、分类与优先级以 [系统测试方案 §3](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 provider 上游模型目录接口（GET /v1/providers/{id}/models）（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-001`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-PMOD-002` 可追到方案清单行与 Run 报告。

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-PMOD-002` / 系统设计 §8 provider 上游模型目录接口（GET /v1/providers/{id}/models） / `VRC-MGMT-001` / `negative` / `P1`
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（ERR-*）
- 方案清单登记：`ST-PMOD-002`（与 §3.2 权威清单一致；本文件名 `st-pmod-002.md`，唯一对应）。
- 要测什么（责任展开）：`GET /v1/providers/{id}/models` 读取不存在 provider 的上游模型目录：HTTP 404 + `error.code=="not_found"`，统一错误信封，无副作用。
- 明确不测什么 / 失败含义：不证明 既存 provider 的正常目录（ST-PMOD-001）、不证明 provider 详情/usage 子路径的 404（ST-PROV-004、ST-PUSAGE-004）、不证明鉴权优先于存在性（ST-AUTH-009）、不证明上游不可用路径（不在本负向 case 范围）。

**目的（被测契约）**：验证 provider 上游模型目录的**未知 provider 负向契约**。被测端点/规则：`GET /v1/providers/{provider_id}/models`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `listProviderModels`，`security=AdminBearerAuth`），认证角色 `admin`；未知 id 由 [`registry.get_provider`](../../../../src/management/registry.py)（`raise ApiError(404,"not_found",…)`，经 [`admin.list_provider_models`](../../../../src/management/admin.py) 先行解析）返回统一错误信封的 `404` + `code=not_found`；`type=request_error`（<500）、`param=null`、`retryable=false`。设计验证项 `VRC-MGMT-001`；错误目录 `ERR-NOTFOUND`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`T-CFG-SECRET`、`CT-ADMIN-001`。**不证明什么**：不证明既存 provider 的正常目录（ST-PMOD-001）、不证明 provider 详情/usage 子路径的 404（ST-PROV-004、ST-PUSAGE-004）、不证明鉴权优先于存在性（ST-AUTH-009）、不证明上游不可用路径（不在本负向 case 范围）。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例；角色 `admin`，只读；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）。执行前必须通过[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go)(../llmtier-system-test-scheme.md) 的 6 项就绪检查（详见 §2.1）；任一失败 → 整班 BLOCKED/SKIP，不得改用模拟路径。fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）：`admin_client`。初始状态：m5air 现有 3 provider / 4 deployment / 7 fixed tier。**自动化入口 `ST-PMOD-002.py` 为 `Implemented`（A 类）。**

## 3. 输入构造

- **输入与构造**：固定请求（无请求体；`{id}` 取保证不存在的字面量）：
  ```http
  GET /v1/providers/provider_does_not_exist_xyz/models HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：`{provider_id}` 取 `provider_does_not_exist_xyz`（不在 §2.1 基线，也不在上游目录）；无 body；不注入故障。**关键顺序**：该端点先经 `get_provider` 解析存在性，未知 id 在触上游 `/models` **之前**即 404（不得让上游请求先发生）。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = admin_client.get("/v1/providers/provider_does_not_exist_xyz/models")`；记录 status、headers、body。
  3. 断言 `resp.status_code == 404`。
  4. `err = resp.json()["error"]`：断言键集恰为 `{message,type,code,param,retryable}`；`err["code"] == "not_found"`、`err["type"] == "request_error"`、`err["param"] is None`、`err["retryable"] is False`。
  5. （交叉核对，不改变判定）`GET /v1/providers/provider_does_not_exist_xyz` 断言同为 `404 not_found`，佐证根因是 provider 不存在而非 `/models` 子路径特例。

**重点关注步骤**：① **状态与 code 双断言**——必须同时 `404` 且 `code==not_found`，只看到 404 不能通过（路由不命中也是 404）；② **信封 identity**——恰 5 键，`type` 由状态导出（404<500 ⇒ `request_error`），无 `category` 键，`param=null`、`retryable=false`；③ **触上游前拒绝**——未知 id 不得触发 `endpoint + /models`（避免把 404 变成上游错误）；④ **零副作用**——只读失败不写任何资源；⑤ **不依赖 message 文本**——Oracle 只约束 code/type/param/retryable；⑥ **不得硬编码其它 404**——不得把鉴权失败/上游失败混入本 case。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ErrorEnvelope`/`ErrorDetail` + `ERR-NOTFOUND` 目录（不依赖实现文案）。
  - HTTP：`404`；`Content-Type: application/json`。
  - body：`{"error":{"code":"not_found","type":"request_error","param":null,"retryable":false,"message":"<nonempty>"}}`（恰 5 键）。
  - 无资源变化，且未触碰上游目录端点。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`status==404` 且 `error.code=="not_found"` 且信封 5 键、`type=="request_error"`、`param is None`、`retryable is False`，且无副作用。
  - **FAIL**：status 非 404（如 200/500）、`code` 不符、信封缺/多键、`type` 错，或未知 id 却触发了上游请求。
  - **BLOCKED**：测试代码/契约本身问题——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用替代路径/伪造 404 冒充——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（§7，`ST-PMOD-002.py`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——负向读失败无写副作用。第/各步列表 GET 的 `query_snapshots` 分页快照（10 分钟 TTL）由服务端自身产生，B 类整班 `rm -rf` 临时目录时随库消失，无需手工删除。 退出前确认 `/readyz` 7 tier、provider 列表未变、无未清空注入。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)(../llmtier-system-test-scheme.md)：Run ID=`<date>/A-api`；保存原始 status/headers/body（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见 §4.8/§10；失败现场不截断。**本 case 额外证据**：`inputs` 为未知 `provider_id`。

- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；`admin_client` fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）；`ErrorEnvelope` 机器契约；实现 `src/management/registry.py` / `src/management/admin.py`；自动化入口 `ST-PMOD-002.py`（`Implemented`）。**不依赖**其它 Case；与 ST-PMOD-001 成对但各自独立。

> 实现状态：Implemented（`ST-PMOD-002.py`）；执行状态与 Verdict 只在 Run 报告。
