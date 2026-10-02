<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-OBSDEPL-004 — 非法注入项

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-OBSDEPL-004` |
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
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/cases/ST-OBSDEPL-004.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`ST-OBSDEPL-004`）；责任摘要、分类与优先级以 [系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单) 清单行为准。
- **测试脚本的唯一依据**：编码者按本文档写测试代码，不需要回读方案或设计正文猜测意图。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-OBSDEPL-004` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-OBSDEPL-004` / 系统设计 §8 注入配置接口（/v1/deployments/{id}/diagnostics） / `VRC-DIAG-004` / `negative` / `P1`
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（ERR-*）
- 方案清单登记：`ST-OBSDEPL-004`
- 要测什么（责任展开）：`PATCH /v1/deployments/{id}/diagnostics` 提交非法注入项：HTTP 400 `invalid_injection`（`param` 指向被拒字段），不写入任何注入行。
- 明确不测什么 / 失败含义：不证明 正向写入（ST-OBSDEPL-002）、不证明未知 deployment 的 404（ST-OBSDEPL-003，且存在性优先于本校验）、不证明注入命中（ST-RESP-011/22）、不证明别名等价（ST-OBSALIAS-004）。**实现现状（严格 bool，已对齐 openapi）**：`_validate` 要求 `isinstance(enabled, bool)`，非 bool（含缺失/字符串/整数）→ 400 `invalid_injection` `param="enabled"`（`injections.py:34-36`），与 openapi `InjectionWrite.enabled: boolean` 一致；本 case 正面覆盖该严格校验。

**目的（被测契约）**：验证注入写路径的**项校验负向契约**。被测端点/规则：`_validate` 要求 `type ∈ _TYPES`（否则 `param="type"`）、`config` 为对象（否则 `param="config"`）、每类型必填 `config` 字段（缺失 → `param=<field>`）、`error_body` 为非空字符串（>512B 按 UTF-8 截断）、`malformed_event_type ∈ {invalid_json, unknown_event_type}`、数值字段范围 `delay_ms∈[0,60000]`、`retry_after_sec∈[0,300]`、`stream_terminate_after_events∈[1,10000]`、`malformed_after_events∈[0,10000]` 且必须是 `int`（`bool` 被拒）（[`src/libdiag/injections.py`](../../../../src/libdiag/injections.py)）；
任何非法项 → `ApiError(400, "invalid_injection", ..., param=...)`，**零写入**。设计验证项 `VRC-DIAG-004`；机制 `T-OBS-INJECT`（[observability 机制](../../../20_system_design/mechanisms/observability.md) §4.3.2 `D-OBS-INJECTION-CONFIG`、§5.1 "类型/字段/范围非法 → `ERR-INJECTION`（400）；
校验失败不写、副作用无"）；错误目录 `ERR-INJECTION` → `invalid_injection`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理) `ERR-INJECTION → ST-OBSDEPL-004`）；
需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01..06`、`CT-ADMIN-001`（[系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）；
机器契约 [`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)（`InjectionList`/`InjectionWrite`，400 → `BadRequest`）。
**不证明什么**：不证明正向写入（ST-OBSDEPL-002）、不证明未知 deployment 的 404（ST-OBSDEPL-003，且存在性优先于本校验）、不证明注入命中（ST-RESP-011/22）、不证明别名等价（ST-OBSALIAS-004）。
**实现现状（严格 bool，已对齐 openapi）**：`_validate` 要求 `isinstance(enabled, bool)`，非 bool（含缺失/字符串/整数）→ 400 `invalid_injection` `param="enabled"`（`injections.py:34-36`），与 openapi `InjectionWrite.enabled: boolean` 一致；
本 case 正面覆盖该严格校验。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 附加（B 类）；`depl_b` 存在且 healthy；fixture：`llmtier_b` + `admin_client_b`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。初始状态=基线，`diagnostic_injections` 为空；本 case 期望零写入，结束再次确认库中 `depl_b` 仍为空。

## 3. 输入构造

- **输入与构造**：对**已存在**的 `depl_b` 发起（每个非法项独立 `PATCH`）：
  - 未知 type：`{"items":[{"type":"bogus","config":{},"enabled":true}]}` → 400 `param="type"`
  - `config` 非对象：`{"items":[{"type":"delay","config":"x","enabled":true}]}` → 400 `param="config"`
  - 缺必填字段：`{"items":[{"type":"fault_502","config":{},"enabled":true}]}`（缺 `error_body`）→ 400 `param="error_body"`
  - `error_body` 空串/非串：`{"items":[{"type":"fault_502","config":{"error_body":""},"enabled":true}]}`、`{"error_body":123}` → 400 `param="error_body"`
  - 范围越界：`{"items":[{"type":"delay","config":{"delay_ms":60001},"enabled":true}]}`、`delay_ms:-1`、`{"type":"rate_limit","config":{"retry_after_sec":301}}`、`{"type":"stream_terminate","config":{"stream_terminate_after_events":0}}`、`{"type":"malformed_event","config":{"malformed_after_events":10001,"malformed_event_type":"invalid_json"}}` → 400 `param=<field>`
  - 非 int / bool：`{"items":[{"type":"delay","config":{"delay_ms":"1000"},"enabled":true}]}`、`{"delay_ms":true}` → 400 `param="delay_ms"`
  - 非法枚举：`{"items":[{"type":"malformed_event","config":{"malformed_after_events":1,"malformed_event_type":"bogus"},"enabled":true}]}` → 400 `param="malformed_event_type"`
  - 非数组 items：`{"items":"x"}` → 400 `invalid_injection`（`set_injections` 的列表检查）
  - 数组含一个合法 + 一个非法项：整体 400、**不得部分写入**

  边界点：`enabled` 必须是 JSON 布尔（`isinstance(enabled, bool)`，`injections.py:34-36`）——非 bool/缺失 → 400 `param="enabled"`（本 case 末尾三组样例覆盖）；`delay_ms=0`/`retry_after_sec=0`/`malformed_after_events=0` 是合法端点值（不得误判非法）。

  > **实现 vs openapi（一致）**：openapi `InjectionWrite.enabled` 为**必填 `boolean`**（`required:["type","config","enabled"]`）；实现 `_validate` 严格要求 `isinstance(enabled, bool)`（`injections.py:34-36`），字符串 `"yes"`、整数 `1`、缺省（`None`）均 → 400 `invalid_injection` `param="enabled"`。二者一致，无偏差。本 case 正面覆盖 `enabled` 非 bool 三类样例。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /v1/deployments/depl_b/diagnostics` → 记录 `orig_raw`（应为 `[]`）。
  2. 对每个非法项独立 `PATCH` → 断言 `resp.status_code == 400`。
  3. 每次取 `err`：断言键集恰 5、`err["code"]=="invalid_injection"`、`err["type"]=="request_error"`、`err["retryable"] is False`；对被拒字段，断言 `err["param"]` 等于期望字段名（`type`/`config`/`error_body`/`delay_ms`/`retry_after_sec`/`stream_terminate_after_events`/`malformed_after_events`/`malformed_event_type`）。
  4. 混合项（合法+非法）→ 断言 400 且随后 `GET` 仍为 `orig_raw`（**无部分写入**）。
  5. 全部非法样例后 `GET /v1/deployments/depl_b/diagnostics` → 断言字节等于 `orig_raw`。
  6. （边界对照）合法端点值 `delay_ms=0` / `retry_after_sec=0` → 断言 `200`；随即 `PATCH {"items":[]}` 清空。（可选交叉证据）`GET /v1/audit` 见 `result=="failed"` 行。

**重点关注步骤**：① **存在性优先**——`depl_b` 存在，故进入项校验并返回 400 `invalid_injection`（不是 404）。② **`param` 精确**——指向被拒字段名，而非笼统。③ **无部分写入**——混合项中即使一项合法也整体 400 且不落库（validate 在 txn 之前全量执行）。
④ **范围边界**——`0` 是合法端点值；上限+1 非法；`bool` 是 `int` 子类但必须被拒（`isinstance(value, bool)` 显式排除）。⑤ **`error_body` 512B**——>512B 是**静默截断**（合法），空串/非串才 400；
本 case 不把长串当非法。⑥ **错误信封 identity**——恰 5 键、`type=request_error`。⑦ **`enabled` 严格 bool**——openapi `InjectionWrite` 要求 `enabled` 为必填 `boolean`，实现 `_validate` 同样要求 `isinstance(enabled, bool)`（`injections.py:34-36`）；
非 bool/缺失 → 400 `param="enabled"`，本 case 末尾三组样例正面覆盖（见输入与构造"实现 vs openapi"）。⑧ **零副作用**——非法序列后注入表逐字节不变。⑨ **降级/存储**——`_UnavailableDiagnostics.set_injections` 不校验、返回 `[]` 属降级实例 → BLOCKED/SKIP；
`503 usage_store_unavailable` 判 BLOCKED/SKIP。自动化入口 `ST-OBSDEPL-004.py` 已实现。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `BadRequest`（`ErrorEnvelope`）+ 机制 §4.3.2 `D-OBS-INJECTION-CONFIG` 白名单/范围 + `ERR-INJECTION`。
  - 每个非法项：HTTP `400`；`Content-Type: application/json`；body `{"error":{"message":<str>,"type":"request_error","code":"invalid_injection","param":"<field>","retryable":false}}`（恰 5 键）。
  - 不变量：非法序列后 `GET /v1/deployments/depl_b/diagnostics` 与 `orig_raw` 逐字节相同；混合项无部分写入。
  - 对照：合法端点值 `0` → 200。
  - **fail-open**：降级实例不校验（无法证明契约）→ **BLOCKED/SKIP**；健康实例返回 200/非 `invalid_injection` → **FAIL**；`503 usage_store_unavailable` 判 **BLOCKED/SKIP**。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：所有非法项均 `400 + invalid_injection + type=request_error + retryable=false + param=字段名`；无部分写入；合法边界 `0` 为 200。
  - **FAIL**：任一非法项返回非 400、`code`/`param` 错、接受 `bool`/字符串数值/越界值，或出现部分写入。
  - **BLOCKED**：测试代码/契约问题、降级实例、存储不可达——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：B 类实例不可用、依赖 fixture 未满足——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：无（自动化入口已实现；执行状态见 Run 报告）。
  - **INVALID**：用 mock/替代路径冒充真实实例，或未真正提交非法项却按行为判定——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需数据 teardown**——非法输入零写入；仍须 `GET` 复核 `depl_b` 注入为空，并清空边界对照产生的合法注入（`PATCH {"items":[]}`）。离开前确认无未清空注入项、`/readyz` 7 tier。 B 类整班结束由 fixture `stop()` + `rm -rf` 临时目录（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存每个非法请求 body 与原始 400 信封、混合项无部分写入对比、`orig_raw` 前后、合法边界对照、可选失败审计、命令/exit code/`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/B-api`，`environment:"b"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go)（B 类附加）；`llmtier_b`/`admin_client_b` fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）；`ERR-INJECTION`；`InjectionList`/`InjectionWrite` 机器契约（`enabled` 必填 `boolean`，实现严格校验，一致）；实现 [`src/libdiag/injections.py`](../../../../src/libdiag/injections.py)（`_validate`/`_TYPES`/`_RANGES`/`_CONFIG_FIELDS`）、[`src/http_api/app.py`](../../../../src/http_api/app.py)。自动化入口 `ST-OBSDEPL-004.py`（已实现）。**不依赖**其它 Case；与 ST-OBSDEPL-002（正向写）、ST-OBSDEPL-003（未知 404，存在性优先）互补但各自独立执行。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
