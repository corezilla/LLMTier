<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-OBSDIAG-003 — 开关更新非法值

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-OBSDIAG-003` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-OBSDIAG-003.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`ST-OBSDIAG-003`）；责任摘要、分类与优先级以 [系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单) 清单行为准。
- **测试脚本的唯一依据**：编码者按本文档写测试代码，不需要回读方案或设计正文猜测意图。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-OBSDIAG-003` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-OBSDIAG-003` / 系统设计 §8 诊断开关接口（/v1/diagnostics） / `VRC-DIAG-001` / `negative` / `P2`
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（ERR-*）
- 方案清单登记：`ST-OBSDIAG-003`
- 要测什么（责任展开）：`PATCH /v1/diagnostics` 提交非布尔开关值（含 `null`）：HTTP 400 `invalid_request`（`param` 指向被拒键），开关状态不变、无部分写入。`null` 在 HTTP 层 `_optional_boolean`（`app.py:165-171`）即被 400 拒绝（键在 body 且值非 bool），**不**到达 libdiag `set_switches`，与 openapi `boolean` 一致。
- 明确不测什么 / 失败含义：不证明 合法更新的成功/审计（ST-OBSDIAG-002）、不证明 GET 读契约（ST-OBSDIAG-001）、不证明**未知键**被拒（openapi 虽声明 `additionalProperties:false`，当前 handler 不校验多余键——见重点关注，作为实现/openapi 不一致单独登记）、不证明认证负向（ST-AUTH-008/ST-OBSREQTRACE-003 风格）。**实现现状（已对齐 openapi）**：HTTP 层 `_optional_boolean`（`app.py:165-171`）对 `key in body` 且值非 bool（含 `null`）先抛 400 `invalid_request` `param=key`，故 openapi `boolean` 要求的 400 得到满足。

**目的（被测契约）**：验证 `PATCH /v1/diagnostics` 的**输入校验负向契约**。被测端点/规则：`PATCH /v1/diagnostics`，`set_switches` 对每个传入的非 `None` 值要求 `isinstance(value, bool)`，否则抛 `ApiError(400, "invalid_request", "<name> must be a boolean", param=<name>)`（[`src/libdiag/settings.py`](../../../../src/libdiag/settings.py)）；错误走统一信封 `{error:{message,type,code,param,retryable}}`（`type="request_error"`，`retryable=false`）；校验发生在事务之前，**零副作用**（`diagnostic_settings` 不变、无成功审计；`app.admin.mutate` 失败路径会记一条 `result="failed"` 审计）。设计验证项 `VRC-DIAG-001`；机制 `T-OBS-SWITCH`（[observability 机制](../../../20_system_design/mechanisms/observability.md) §4.3.1/§5.1，`IF-OBS-SWITCH` "校验=非 bool 且非 None → 拒绝；失败无副作用"）；错误目录 `ERR-REQ-VALIDATION` → wire `code=invalid_request`（[系统设计 §7.8](../../../20_system_design/llmtier-system-design.md)）；需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01`/`R-OBS-02`、`CT-ADMIN-001`（[系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）；机器契约 [`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)（`DiagnosticsSwitchPatch`，400 → `BadRequest`）。**不证明什么**：不证明合法更新的成功/审计（ST-OBSDIAG-002）、不证明 GET 读契约（ST-OBSDIAG-001）、不证明**未知键**被拒（openapi 虽声明 `additionalProperties:false`，当前 handler 不校验多余键——见重点关注，作为实现/openapi 不一致单独登记）、不证明认证负向（ST-AUTH-008/ST-OBSREQTRACE-003 风格）。**实现现状（已对齐 openapi）**：HTTP 层 `_optional_boolean`（`app.py:165-171`）对 `key in body` 且值非 bool（含 `null`）先抛 400 `invalid_request` `param=key`，故 openapi `boolean` 要求的 400 得到满足。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 附加（B 类）；执行前附加（B 类）实例可启动、`/healthz` 200、`prov_b`+`depl_b`+7 tier、`depl_b` healthy、LAN fake provider；fixture：`llmtier_b` + `admin_client_b`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。初始状态=基线；`diagnostic_settings` 单行默认 `{false,false}`。本 case 期望零写入，故**不改变开头状态**；仍须在结尾核验状态未变。

## 3. 输入构造

- **输入与构造**：先 `GET /v1/diagnostics` 记录 `orig_raw`，再对每种非法输入独立发起（每次前确保开关仍是 `orig`）：
  - `{"snapshots_enabled": "yes"}`（字符串）
  - `{"snapshots_enabled": 1}`（整数——注意 Python `isinstance(1, bool) is False`，必须拒）
  - `{"stats_enabled": null}`（显式 `null`：HTTP 层 `_optional_boolean` 见 `key in body` 且值非 bool ⇒ **400 `invalid_request` `param="stats_enabled"`**；不会到达 `set_switches`。openapi `DiagnosticsSwitchPatch` 把两键声明为 `boolean`（无 `nullable`），400 与之一致。）
  - `{"stats_enabled": "true"}` / `{"stats_enabled": 0}`（字符串/整数）
  - `{"snapshots_enabled": []}`（数组）、`{"stats_enabled": {}}`（对象）

  请求：`PATCH /v1/diagnostics`、`Authorization: Bearer dev-admin`、`Content-Type: application/json`。  边界点：每种非法值（含 `null`）必须命中 400 且 `param` 等于该键名；HTTP 层 `_optional_boolean` 对 `null` 与 openapi `boolean` 一致地返回 400。

  > **实现 vs openapi（一致）**：`DiagnosticsSwitchPatch` 将 `snapshots_enabled`/`stats_enabled` 声明为 `"type":"boolean"`（`additionalProperties:false`，不可空）。HTTP 层 `_optional_boolean`（`app.py:165-171`）在键存在且值非 bool 时即抛 `ApiError(400, "invalid_request", "<name> must be a boolean", param=<name>)`，故 `{"stats_enabled": null}` ⇒ **400**。libdiag `set_switches`（`settings.py:18-21`）本身对 `None` 跳过，但 `null` 已被 HTTP 层先拦截，永不到达。二者与 openapi 一致，无冲突。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /v1/diagnostics` → 记录 `orig_raw`。
  2. 对每个非法 body（上述字符串/整数/数组/对象样例）逐个 `PATCH`；每个后立即 `GET` 复核开关未变。
  3. 每次断言 `resp.status_code == 400`；`err = resp.json()["error"]`：`err["code"]=="invalid_request"`、`err["type"]=="request_error"`、`err["retryable"] is False`、`err["param"]` 等于被拒键名（`snapshots_enabled` 或 `stats_enabled`）。
  4. 全部非法样例后 `GET /v1/diagnostics` → 断言字节等于 `orig_raw`（无任何写入）。
  5. `PATCH` body `{"stats_enabled": null}` → 断言 `400 invalid_request`（HTTP 层 `_optional_boolean` 拦截 `null`）；随后 `GET` 确认开关未变。
  6. （可选交叉证据）`GET /v1/audit` → 断言非法尝试对应 `result=="failed"` 的 `diagnostics.switch.update` 行存在，且**不存在**由本 case 产生的成功行。

**重点关注步骤**：① **bool vs int**——`1`/`0` 必须是非法（Python 中 `bool` 是 `int` 子类，但校验用的是 `isinstance(value, bool)`，故 `1` 被拒）；若观测到 `1` 被接受为 `true`，判 FAIL。② **`param` 精确性**——必须指向被拒字段名，而非笼统。③ **零副作用**——400 后 `diagnostic_settings` 逐字节不变，不得出现"一半写入"（例如先写 `snapshots_enabled` 再在 `stats_enabled` 校验失败）。④ **失败审计**——`mutate` 失败路径记 `result="failed"`；不得把失败审计当作契约成功。⑤ **`null` 的处置**——HTTP 层 `_optional_boolean`（`app.py:165-171`）对 `key in body` 且值非 bool（含 `null`）抛 400；故 `{"stats_enabled": null}` 与 openapi `boolean` 一致地返回 400（不会到达 libdiag `set_switches`）。⑥ **未知键差异（登记）**——`DiagnosticsSwitchPatch` openapi `additionalProperties:false`，但实现忽略多余键；本 case 可在报告中作为**已知不一致**记录：`{"snapshots_enabled": true, "bogus": 1}` 当前预期 200（实现）而契约声明应 400——本 case 的 PASS 判据**不含**未知键，避免混淆。⑦ **降级/存储**——`_UnavailableDiagnostics.set_switches` 不校验直接返回默认，属降级实例（本 case 无法证明校验逻辑）→ BLOCKED/SKIP；`503 usage_store_unavailable` 判 BLOCKED/SKIP。自动化入口 `at_obs_diag_03.py` 已实现。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `BadRequest`（`ErrorEnvelope`）+ 机制 §5.1 `IF-OBS-SWITCH` 校验语义 + 错误目录 `ERR-REQ-VALIDATION`。
  - 每个非法输入：HTTP `400`；`Content-Type: application/json`；body `{"error":{"message":"<name> must be a boolean","type":"request_error","code":"invalid_request","param":"<name>","retryable":false}}`（恰 5 键；openapi 未为 200/400 声明响应头）。
  - 状态不变量：非法序列后 `GET /v1/diagnostics` 与 `orig_raw` 逐字节相同。
  - 一致性项：`{"stats_enabled": null}` 因 HTTP 层 `_optional_boolean` ⇒ `400`，与 openapi `boolean` 一致。
  - **fail-open**：降级实例（`_UnavailableDiagnostics`）不执行校验、恒返回默认——本 case 依赖真实校验，降级下判 BLOCKED/SKIP，**不**把默认值当 PASS。存储不可达 503 `usage_store_unavailable` 判 BLOCKED/SKIP。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：所有非法样例（含 `null`）均 `400 + invalid_request + type=request_error + retryable=false + param=键名`，且状态逐字节不变。
  - **FAIL**：任一非法值（含 `null`）返回非 400、`code`/`type`/`param` 错、接受了 `1`/`0`/字符串/`null`，或出现部分写入/状态改变。
  - **BLOCKED**：测试代码/契约本身问题或降级实例无法证明校验、存储不可达——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：B 类实例不可用、依赖 fixture 未满足——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：无（自动化入口已实现；执行状态见 Run 报告）。
  - **INVALID**：用 mock/替代路径冒充真实实例，或未真正提交非法 body 却按行为判定——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需数据 teardown**——非法输入零写入，`diagnostic_settings` 保持初值；仍须 `GET` 复核并确认无残留。离开前确认开关初值、`/readyz` 7 tier、无未清空注入项。 B 类整班结束由 fixture `stop()` + `rm -rf` 临时目录（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存每个非法请求 body 与原始 400 信封、`GET` 前后 `orig_raw` 对比、失败审计行（可选）、`null` 对照、命令/exit code/`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/B-api`，`environment:"b"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go)（B 类附加）；`llmtier_b`/`admin_client_b` fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）；`diagnostic_settings`；`DiagnosticsSwitchPatch` 机器契约（`boolean`、`additionalProperties:false`，`null` 由 HTTP 层 400）；实现 [`src/libdiag/settings.py`](../../../../src/libdiag/settings.py)、[`src/http_api/app.py`](../../../../src/http_api/app.py)（`_optional_boolean` `app.py:165-171`）。自动化入口 `at_obs_diag_03.py`（已实现）。**不依赖**其它 Case；与 ST-OBSDIAG-002（合法更新成功）互为正向/负向，各自独立执行。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
