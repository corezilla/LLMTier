<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-RUNTIME-001 — 运行时快照

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-RUNTIME-001` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-RUNTIME-001.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-RUNTIME-001`）；责任摘要、分类与优先级以 [系统测试方案 §3](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 运行态接口（GET /v1/runtime）（parent `llmtier-system-design`），设计验证项 `VRC-INF-004`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-RUNTIME-001` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-RUNTIME-001` / 系统设计 §8 运行态接口（GET /v1/runtime） / `VRC-INF-004` / `normal` / `P1`
- **测试方法（§1.5 方法表行）**：等价类划分 + 契约字段比对
- 方案清单登记：`ST-RUNTIME-001`（与 §3.2 权威清单一致；本文件名 `st-runtime-001.md`，唯一对应）。
- 要测什么（责任展开）：`GET /v1/runtime` 返回运行时并发/队列快照：HTTP 200 + `{deployments,providers,queues}`。
- 明确不测什么 / 失败含义：不证明 data 角色的 403 负向（ST-RUNTIME-002）、不证明具体并发数值（运行时动态，不设门限）、不证明队列上限/429（ST-RESP-020 的领域）。

**目的（被测契约）**：验证**运行时快照读契约**。被测端点/规则：`GET /v1/runtime`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `getRuntimeSnapshot`，`security=AdminBearerAuth`，响应 schema `type: object`）；[`Router.snapshot`](../../../../src/inference/routing.py) 在条件锁内读 `deployment_runtime_profiles`/`provider_usage_profiles` 并返回 `deployments{id:{running,max_concurrent}}`、`providers{id:{running,max_concurrent,min_request_interval_ms,requests_per_minute}}`、`queues{tier:len}`（只含非空队列）。设计验证项 `VRC-INF-004`；需求/机制链 `LT-FUN-005`、`LT-OPS-002`、`R-INF-03`、`CT-OPS-001`。**不证明什么**：不证明 data 角色的 403 负向（ST-RUNTIME-002）、不证明具体并发数值（运行时动态，不设门限）、不证明队列上限/429（ST-RESP-020 的领域）。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `admin_client`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；初始状态=§2.3 A 类基线（3 provider / 4 deployment / 7 fixed tier）。快照只读。

## 3. 输入构造

- **输入与构造**：
  ```http
  GET /v1/runtime HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：无 body、无 query；凭据固定 `admin`；不注入故障；不构造非法输入。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = admin_client.get("/v1/runtime")`；记录 status、headers、body。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`。
  4. 解析 body：断言为对象且含 `deployments`、`providers`、`queues` 三键；断言 `deployments` 与 `providers` 均为对象（dict），`queues` 为对象。
  5. 抽查 `providers` 元素键集含 `{running,max_concurrent,min_request_interval_ms,requests_per_minute}`（`Router.snapshot` 契约，`routing.py:59-67`）；`deployments` 元素键集含 `{running,max_concurrent}`。
  6. （可选）抽查 `deployments` 的键 ⊆ `GET /v1/deployments` 的 id 集合（快照与注册表一致，不出现未知 deployment）。

**重点关注步骤**：① **三键齐全**——OpenAPI 仅声明 `type: object`，但实现契约固定 `{deployments,providers,queues}`；缺键即 FAIL；② **类型正确**——`providers`/`deployments` 必须是 id→对象 的映射，不是数组；③ **不设数值门限**——`running`/`max_concurrent` 为运行时动态值，只断言存在与类型，不硬编码具体数；④ **`queues` 可空**——只含非空队列，空实例可为 `{}`，不得因空 FAIL；⑤ **纯读**——`GET` 不写库（不创建 `query_snapshots`），不改 version；⑥ **一致性**——`deployments` 键应来自 `deployment_runtime_profiles`，与注册表一致。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `Router.snapshot` 的字段契约 + `openapi` `/v1/runtime` 200。
  - HTTP：`200`；`Content-Type: application/json`。
  - body：`{"deployments":{...},"providers":{...},"queues":{...}}`；`providers` 元素含 `running`/`max_concurrent`/`min_request_interval_ms`/`requests_per_minute`；`deployments` 元素含 `running`/`max_concurrent`。
  - 无错误信封。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`200` + 三键齐全 + `providers`/`deployments` 为 dict 且元素含规定键、`queues` 为 dict。
  - **FAIL**：status 非 200、缺键、类型错（如数组）、或出现错误信封。
  - **BLOCKED**：fixture/断言逻辑问题——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充真实 m5air——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——纯读，不改并发/队列/配置。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存原始 HTTP status/headers/body、发出命令、exit code、`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；`admin_client` fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）；`Router.snapshot`；机制 `R-INF-03`。自动化入口 [`at_adm_runtime_01.py`](../../../../tests/system/api_test_v03/at_adm_runtime_01.py)。**不依赖**其它 Case；与 ST-RUNTIME-002（data 角色负向）互补。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
