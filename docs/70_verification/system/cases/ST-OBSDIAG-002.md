<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-OBSDIAG-002 — 更新诊断开关

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-OBSDIAG-002` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-OBSDIAG-002.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`ST-OBSDIAG-002`）；责任摘要、分类与优先级以 [系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单) 清单行为准。
- **测试脚本的唯一依据**：编码者按本文档写测试代码，不需要回读方案或设计正文猜测意图。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-OBSDIAG-002` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-OBSDIAG-002` / 系统设计 §8 诊断开关接口（/v1/diagnostics） / `VRC-DIAG-001` / `normal` / `P1`
- **测试方法（§1.5 方法表行）**：等价类划分 + 契约字段比对
- 方案清单登记：`ST-OBSDIAG-002`
- 要测什么（责任展开）：`PATCH /v1/diagnostics` 更新全局诊断开关：HTTP 200 + 返回更新后的精确 `SwitchState`，开关持久化到 `diagnostic_settings` 单行，且副作用 = **同事务审计**（`action=diagnostics.switch.update`，`target=diagnostics`）。
- 明确不测什么 / 失败含义：不证明 非法值的 400 拒绝（ST-OBSDIAG-003）、不证明 GET 纯读无副作用（ST-OBSDIAG-001）、不证明别名 PATCH 逐字节等价（ST-OBSALIAS-001）、不证明开关对快照/统计**写入门控**的业务效果（由 ST-OBSSNAP-001、ST-OBSSTATS-001 的数据断言与 observability 机制 `INV-4`/`CON-OBS-001` 承接）、不证明 trace 无开关始终写。

**目的（被测契约）**：验证 Observability `PATCH /v1/diagnostics` 的**开关写契约**。被测端点/规则：`PATCH /v1/diagnostics`，body 为 `DiagnosticsSwitchPatch`（`snapshots_enabled?`、`stats_enabled?` 两个可选布尔，`additionalProperties:false`）；部分更新语义（缺省键保持原值）；成功返回 `SwitchState`（恰 2 个 JSON 布尔）；写 `diagnostic_settings.singleton=1` 单行并**在同一事务**写审计；非法值（非布尔）→ 400 `invalid_request`（属 ST-OBSDIAG-003，本 case 只走合法输入）；认证角色 `admin`；失败走统一错误信封 `{error:{message,type,code,param,retryable}}`（401 `authentication_required` / 403 `permission_denied` / 503 `usage_store_unavailable`）。设计验证项 `VRC-DIAG-001`；机制 `T-OBS-SWITCH`（见[observability 机制](../../../20_system_design/mechanisms/observability.md) §4.3.1/§5.1，`IF-OBS-API-SWITCH`/`IF-OBS-SWITCH`，副作用=同事务审计）；需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01`/`R-OBS-02`、`CT-ADMIN-001`/`CT-LOG-001`（[系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）；机器契约 [`interfaces/openapi/llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)（`SwitchState`/`DiagnosticsSwitchPatch`，`security=AdminBearerAuth`）。**不证明什么**：不证明非法值的 400 拒绝（ST-OBSDIAG-003）、不证明 GET 纯读无副作用（ST-OBSDIAG-001）、不证明别名 PATCH 逐字节等价（ST-OBSALIAS-001）、不证明开关对快照/统计**写入门控**的业务效果（由 ST-OBSSNAP-001、ST-OBSSTATS-001 的数据断言与 observability 机制 `INV-4`/`CON-OBS-001` 承接）、不证明 trace 无开关始终写。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 附加（B 类）；`_baseline_settings` 注入 1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier；`llmtier_b` fixture 的 `depl_b` probe 为 `healthy`；`prov_b.endpoint` 为 LAN IP 上的 fake provider（TS-003）。fixture：`llmtier_b`、`admin_client_b`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。初始状态=1 provider / 1 deployment / 7 tier，`diagnostic_settings` 单行默认 `{snapshots_enabled:false, stats_enabled:false}`。**写 case：本 case 改变开关，必须 teardown 恢复原值**（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 3. 输入构造

- **输入与构造**：先 `GET /v1/diagnostics` 记录原值 `(orig_snapshots, orig_stats)`，再发起部分更新：
  `PATCH /v1/diagnostics HTTP/1.1`、`Authorization: Bearer dev-admin`、`Content-Type: application/json`，body：

  ```json
  {"snapshots_enabled": true}
  ```

  边界/构造点：**部分更新**——只给 `snapshots_enabled`，`stats_enabled` 必须保持原值（验证缺省键不重置）；随后再发一个**全量更新** body `{"snapshots_enabled": true, "stats_enabled": true}` 验证两键同时生效；再发 `{}`（无键）验证返回当前值且无值变化（幂等空更新）。不构造非法值（非布尔属 ST-OBSDIAG-003）；不注入故障；凭据固定 `admin`（`dev-admin`，无 `X-Principal-ID`，故审计 `actor="operator"`）。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /v1/diagnostics`（`admin_client_b`）→ 记录 `orig = {snapshots_enabled, stats_enabled}` 与 `orig_raw` 字节（teardown 用）。
  2. `PATCH /v1/diagnostics` body `{"snapshots_enabled": true}` → 断言 `status_code == 200`；解析 `SwitchState`，断言 `snapshots_enabled is True` 且 `stats_enabled == orig.stats_enabled`（缺省键保持）。
  3. `GET /v1/diagnostics` → 断言与步骤 2 返回一致（写入已持久化，非仅回显）。
  4. `PATCH /v1/diagnostics` body `{"snapshots_enabled": true, "stats_enabled": true}` → 200 且两键均为真。
  5. `PATCH /v1/diagnostics` body `{}` → 200 且返回与步骤 4 相同的 `SwitchState`（空更新幂等、无值变化）。
  6. `GET /v1/audit?limit=...`（`admin_client_b`）→ 在 `data[]` 中定位本次三条 `action=="diagnostics.switch.update"`、`target=="diagnostics"`、`result=="success"`、`actor=="operator"` 的审计行；断言存在（副作用证明）。
  7. `GET /v1/trace/{任意} ` 不在本 case 范围；不做无关键断言。
  8. （teardown，`finally` 内）`PATCH /v1/diagnostics` body `{"snapshots_enabled": orig.snapshots_enabled, "stats_enabled": orig.stats_enabled}` → 200；再 `GET` 校验已回到 `orig_raw`。

**重点关注步骤**：① **部分更新语义**——只给一键时另一键**不得被重置**（`set_switches(None)` 表示保持）；这是本 case 第一断点。② **写入持久化**——步骤 3 的二次 `GET` 必须读到新值，否则只是回显未落库。③ **同事务审计**——`PATCH` 成功必须在 `GET /v1/audit` 出现 `diagnostics.switch.update` 成功行；审计缺失即 FAIL（机制 §5.1 明确 PATCH 才有此副作用，GET 没有）。④ **空更新幂等**——`{}` 不得翻转任何值；不得因缺键报错。⑤ **不改变 trace**——PATCH 不新增 `trace_events`（开关写不是请求路径事件）。⑥ **未知键的行为差异（须登记）**：`DiagnosticsSwitchPatch` 在 openapi 声明 `additionalProperties:false`，但 handler 仅 `body.get("snapshots_enabled")/get("stats_enabled")`，**不校验多余键**；本 case 不把"多余键被拒"列入 Oracle，另在报告中登记该 openapi/实现不一致。⑦ **teardown 完整性**——`finally` 必须恢复原值并二次 `GET` 校验，绝不把开关留在非初态影响同 session 的 OBS-SNAP/STATS 后续 case。⑧ **降级/存储不可达**——`_UnavailableDiagnostics.set_switches` 返回常量 `{false,false}` 且不写审计（fail-open 实例属缺省观测子系统；健康实例的 200+PASS 见 Oracle）；存储异常由 `_store_read`/`mutate` 归 503 `usage_store_unavailable`（环境问题，判 BLOCKED/SKIP，非契约 FAIL）。自动化入口 `ST-OBSDIAG-002.py` 已实现（落位遵循 §4.9/§8.5）。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `SwitchState` wire 形态 + 机制 §4.3.1/§5.1 的"同事务审计"保证（不依赖实现内部）。
  - `PATCH`（合法）：HTTP `200`；`Content-Type: application/json`（openapi 未为 200 声明任何响应头）。
  - body：JSON 对象，键集**恰为** `{snapshots_enabled, stats_enabled}`，两值均为 JSON 布尔；返回值等于更新后持久状态。
  - 部分更新：仅传入键改变，其余保持原值。
  - 审计（独立交叉证据）：`GET /v1/audit` 存在 `action=="diagnostics.switch.update"`、`target=="diagnostics"`、`result=="success"`、`actor=="operator"` 的行（`AuditLog.page` wire：`{data:[{id,actor,action,target,result,created_at,request_id}], page:{has_more,next_cursor}}`）。
  - **fail-open 规则**：诊断子系统初始化失败时 `_UnavailableDiagnostics.set_switches` 返回默认 `{false,false}` 且不写开关/审计——这是**观测降级**，因本 case 断言依赖真实 `diagnostic_settings` 行与审计，降级实例下应判 **BLOCKED/SKIP**（无法证明契约），**不**把降级默认值当 PASS。反之健康实例返回非 200、body 键集/类型不符、或缺失审计 → **FAIL**。`503 usage_store_unavailable`（`ERR-STORE`，见[observability 机制](../../../20_system_design/mechanisms/observability.md) §4.8.1）判 **BLOCKED/SKIP**。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`PATCH` 合法输入 `200` 且 body 为精确 `SwitchState` 且部分更新保持缺省键；写入经二次 `GET` 确认持久；`GET /v1/audit` 存在对应成功审计行；teardown 恢复原值成功。
  - **FAIL**：任一断言不符——status 非 200、键集/类型不符、部分更新重置了另一键、审计缺失、或写未持久。
  - **BLOCKED**：测试代码/契约本身问题（fixture 写不出、断言逻辑错、openapi 语义不清、审计不可读、降级实例无法证明契约）或存储不可达 `503 usage_store_unavailable`——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：B 类临时实例不可用、`provider_endpoint_b` 无 LAN IP（TS-003）、依赖 fixture 未满足——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：无（自动化入口已实现；执行状态见 Run 报告）。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 B 类路径，或未命中真实 `diagnostic_settings` 却按行为判定——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。

## 6. 错误路径、副作用与清理

- **清理与复位**：**必须 teardown（`finally` 强制）**——`PATCH /v1/diagnostics` 恢复 `(orig_snapshots, orig_stats)`，二次 `GET` 校验回到 `orig_raw`。不创建/删除资源，不写注入项，不新增 trace。离开前确认开关回到初值、`/readyz` 仍 7 tier、无未清空注入项。 B 类整班结束由 fixture `stop()` + `rm -rf` 临时目录（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存 `GET` 原值、三条 `PATCH` 请求/响应（status/headers/body）、二次 `GET` 复核、`GET /v1/audit` 审计行、teardown `PATCH` 与最终 `GET`、命令/exit code/`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/B-api`，`environment:"b"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查（B 类附加）；`llmtier_b`/`admin_client_b` fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）；M007 `diagnostic_settings` 单行（`002_observability.sql`）；`SwitchState`/`DiagnosticsSwitchPatch` 机器契约（[`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)）；实现 [`src/libdiag/settings.py`](../../../../src/libdiag/settings.py)、[`src/http_api/app.py`](../../../../src/http_api/app.py)（`app.admin.mutate` 同事务审计）。自动化入口 `ST-OBSDIAG-002.py`（已实现）。**不依赖**其它 Case；与 ST-OBSDIAG-001（GET 纯读）、ST-OBSDIAG-003（非法值 400）、ST-OBSALIAS-001（别名 PATCH 等价）语义相邻但各自独立执行。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
