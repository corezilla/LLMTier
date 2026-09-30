<!-- STD_DOCUMENT_COVER_BEGIN -->
# OBS-STATS-01 — 诊断统计窗口

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `OBS-STATS-01` |
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
| Canonical Path | `docs/70_verification/specifications/cases/obs-stats-01.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`OBS-STATS-01`）；责任摘要、分类与优先级以 [系统测试方案 §3 覆盖分母与 Case 清单](../../schemes/llmtier-system-test-scheme.md#3-覆盖分母与-case-清单) 清单行为准。
- **测试脚本的唯一依据**：编码者按本文档写测试代码，不需要回读方案或设计正文猜测意图。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `OBS-STATS-01` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`OBS-STATS-01` / 系统设计 §8 诊断统计接口（/v1/diagnostics/stats） / `VRC-DIAG-002` / `normal` / `P1`
- 方案清单登记：`OBS-STATS-01`
- 要测什么（责任展开）：`GET /v1/diagnostics/stats` 返回按小时桶聚合的 `StatsView`：顶层恰 `{windows}`，每窗口为恰好 13 键的 `StatsWindow`（状态分布、请求/错误计数、4xx/5xx、延迟分位）。
- 明确不测什么 / 失败含义：不证明 缺 `since`/`until` 的 400（OBS-STATS-02）、不证明 `stats_enabled` 写入门控的业务效果（机制 `INV-4`/`CON-OBS-001`）、不证明 `/v1/stats`（管理面聚合，ADM-STATS-01..03）、不证明快照/trace（OBS-SNAP-01、OBS-TRACE-01）、不证明别名等价（OBS-ALIAS-05）。

**目的（被测契约）**：验证 Observability `GET /v1/diagnostics/stats` 的**只读聚合契约**。被测端点/规则：`GET /v1/diagnostics/stats?since=<RFC3339>&until=<RFC3339>[&deployment_id=&model=]`，`since`/`until` **必填**；返回 `StatsView`（顶层键集恰 `{windows}`）；每 `StatsWindow` 必填 13 键（`stat_hour, deployment_id, model, status_breakdown, error_4xx_count, error_5xx_count, request_count, error_count, latency_p50_ms, latency_p95_ms, latency_min_ms, latency_max_ms, latency_sum_ms`）；`stat_hour` 匹配 `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}$`（小时桶）；认证 `admin`；失败走统一信封 `{error:{message,type,code,param,retryable}}`（401/403/503）。设计验证项 `VRC-DIAG-002`；机制 `T-OBS-STATS`（[observability 机制](../../../20_system_design/mechanisms/observability.md) §4.2 `D-OBS-STATS`、§4.9、§4.10 "统计持久、样本缺失时百分位为 null 而非 0"）；需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01..06`、`CT-ADMIN-001`（[系统测试方案 §3 覆盖分母与 Case 清单](../../schemes/llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）；机器契约 [`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)（`StatsView`/`StatsWindow`，`security=AdminBearerAuth`）。**不证明什么**：不证明缺 `since`/`until` 的 400（OBS-STATS-02）、不证明 `stats_enabled` 写入门控的业务效果（机制 `INV-4`/`CON-OBS-001`）、不证明 `/v1/stats`（管理面聚合，ADM-STATS-01..03）、不证明快照/trace（OBS-SNAP-01、OBS-TRACE-01）、不证明别名等价（OBS-ALIAS-05）。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `admin_client`（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；初始状态=§2.3 A 类基线；`stats_enabled` 默认 false，若从未开启过统计，`windows` 可能为空——**本 case 为形状/类型断言，不以非空为 PASS 前提**。本 case 纯读，初态即终态。

## 3. 输入构造

- **输入与构造**：固定请求（无 body，时间窗取足够宽以容纳现有数据）：
  `GET /v1/diagnostics/stats?since=2000-01-01T00:00:00Z&until=2100-01-01T00:00:00Z`、`Authorization: Bearer dev-admin`、`Accept: application/json`。边界点：`since`/`until` 必须是 RFC3339 date-time；实现按 `since[:13]`/`until[:13]` 取小时桶（[`src/libdiag/stats.py`](../../../../src/libdiag/stats.py)）；不构造缺参（OBS-STATS-02）；不注入、不写入；`windows` 是否非空不固定。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz`（§2.1，自动执行）。
  2. `GET /v1/diagnostics/stats?since=...&until=...`（`admin_client`）→ 记录 status/`Content-Type`/原始 body。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`。
  4. 解析 JSON，断言顶层键集**恰为** `{windows}`；`windows` 为数组。
  5. 对每个 `window`：断言键集**恰为** 13 键；`stat_hour` 匹配 `^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}$`；`deployment_id`/`model` 为字符串或 `null`；`status_breakdown` 为对象（值 ∈ 非负整数）；`error_4xx_count`/`error_5xx_count`/`request_count`/`error_count` 为非负整数；`latency_p50_ms`/`latency_p95_ms`/`latency_min_ms`/`latency_max_ms` 为 `null` 或数值；`latency_sum_ms` 为数值（≥0；无样本为 0）。
  6. （`deployment_id`/`model` 过滤交叉核对，不改变判定）带 `&deployment_id=dep_omlx_qwen36` 再请求一次，断言 200 且过滤窗口的 `deployment_id` 均等于该值；本 case 不承担过滤语义判定。

**重点关注步骤**：① **顶层键集精确**——恰 `{windows}`（`additionalProperties:false`）；② **窗口键集精确**——恰 13 键；③ **`stat_hour` 形状**——小时桶字符串，不是完整 timestamp、不是毫秒；④ **计数类型**——计数键必须是非负整数（不是字符串/浮点/`null`）；⑤ **百分位 `null` vs 0**——无延迟样本时 `latency_p50/p95/min/max` 必须为 `null`，`latency_sum_ms` 为 `0`（机制 §4.10 明确"样本缺失 → null 而非 0"）；⑥ **空 `windows` 合法**——`stats_enabled=false` 或无数据时 `{"windows":[]}` 仍合法形状（PASS），**不得**因空判 FAIL；⑦ **降级/存储**——`_UnavailableDiagnostics.stats` 恒返回 `{"windows":[]}` 的 **200**（fail-open，形状 PASS）；`503 usage_store_unavailable` 判 BLOCKED/SKIP。注意：本 case 当前 `MISSING`（§3.2），无 `at_obs_stats_01.py`。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `StatsView`/`StatsWindow` wire 形态 + 机制 §4.2/§4.10 聚合语义（不依赖实现内部计数）。
  - HTTP：`200`；`Content-Type: application/json`（openapi 未为 200 声明响应头）。
  - body：`{"windows":[...]}`，顶层键集恰 1；每窗口恰 13 键且类型/范围/`stat_hour` 形状如上。
  - 空窗口：`windows=[]` 合法。
  - **fail-open**：降级实例 `200 + {"windows":[]}` → **PASS**（本 case 不要求非空）；健康实例非 200、键集/类型/形状不符、百分位该 `null` 却为 `0` → **FAIL**；`503 usage_store_unavailable` 判 **BLOCKED/SKIP**。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`200` + `{windows}` 顶层键集 + 每窗口恰 13 键且类型/范围/`stat_hour` 正确（含空窗口 fail-open）。
  - **FAIL**：非 200（存储健康时）、键集不符、计数非整数、`stat_hour` 形状错、或样本缺失百分位错为 0。
  - **BLOCKED**：测试代码/契约问题或存储不可达 `503 usage_store_unavailable`——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：自动化入口 `MISSING`（§3.2），本轮未执行；缺口引用见 §9。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air，或未命中真实诊断服务却按行为判定——见[系统测试计划 §7 报告产出与 Gate 规则](../../plans/llmtier-system-test-plan.md#7-报告产出与-gate-规则)。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——纯读，不写 `data_plane_stats`/`data_plane_latency_samples`、不改开关、不注入。退出前确认无未清空注入项、`/readyz` 仍 7 tier。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存原始 HTTP status/headers/body、命令/exit code/`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../../plans/llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../../plans/llmtier-system-test-plan.md#3-执行前检go--no-go) 6 项就绪检查；`admin_client` fixture（[系统测试计划 §5 环境操作](../../plans/llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../../schemes/llmtier-system-test-scheme.md)）；M007 `data_plane_stats`/`data_plane_latency_samples`（`002_observability.sql`）；`StatsView`/`StatsWindow` 机器契约；实现 [`src/libdiag/stats.py`](../../../../src/libdiag/stats.py)、[`src/http_api/app.py`](../../../../src/http_api/app.py)。自动化入口 `at_obs_stats_01.py`（**当前 `MISSING`，尚未实现**）。**不依赖**其它 Case；与 OBS-STATS-02（缺参 400）、OBS-DIAG-02（开关写）语义相邻但各自独立执行。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
