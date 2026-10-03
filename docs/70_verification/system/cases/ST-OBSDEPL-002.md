<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-OBSDEPL-002 — 写入故障注入

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-OBSDEPL-002` |
| Document Version | `0.1.0-draft.4` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-29` |
| Last Modified Date | `2026-10-03` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/cases/ST-OBSDEPL-002.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`ST-OBSDEPL-002`）；责任摘要、分类与优先级以 [系统测试方案 §6 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单) 清单行为准。
- **测试脚本的唯一依据**：编码者按本文档写测试代码，不需要回读方案或设计正文猜测意图。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-OBSDEPL-002` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-OBSDEPL-002` / 系统设计 §8 注入配置接口（/v1/deployments/{id}/diagnostics） / `VRC-DIAG-004` / `normal` / `P0`
- **测试方法（§2.2 方法表行）**：等价类划分 + 契约字段比对
- 方案清单登记：`ST-OBSDEPL-002`
- 要测什么（责任展开）：`PATCH /v1/deployments/{id}/diagnostics` 写入故障注入：HTTP 200 + 返回更新后的 `InjectionView[]`，按 `(deployment_id, type)` upsert 生效，副作用 = **同事务审计**。
- 明确不测什么 / 失败含义：不证明 注入对推理的**命中效果**（ST-RESP-011/22 在 B 类以真实 `POST /v1/responses` 证明 `fault_502`/`fault_503` 命中；本 case 只证明"配置写入并可由 GET 读回"）、不证明非法项 400（ST-OBSDEPL-004）、不证明未知 deployment 404（ST-OBSDEPL-003）、不证明别名等价（ST-OBSALIAS-004）。
  **实现现状（已对齐 openapi）**：`InjectionList` openapi `required:["items"]`；handler 在 PATCH 前检查 `if "items" not in body: raise ApiError(400, "invalid_request", ...)`（`app.py:331-332` 扁平、`app.py:341-342` 别名），故缺 `items` 是 **400**，不会静默 revoke。
  本 case 用规范 body。

**目的（被测契约）**：验证 `PATCH /v1/deployments/{deployment_id}/diagnostics` 的**注入写契约**。被测端点/规则：request body `InjectionList`（键集必须含 `items`，每项 `InjectionWrite = {type, config, enabled}`）；
成功返回全量 `InjectionView[]`；按 `(deployment_id, injection_type)` upsert（幂等）；`enabled=true` 才生效；写在同一事务写审计（`action=diagnostics.injection.update`，`target=<deployment_id>`）；
未知 deployment → 404 `not_found`（ST-OBSDEPL-003）；非法项 → 400 `invalid_injection`（ST-OBSDEPL-004）；认证 `admin`；统一信封 5 键。设计验证项 `VRC-DIAG-004`；
机制 `T-OBS-INJECT`（[observability 机制](../../../20_system_design/mechanisms/observability.md) §4.3.2 `D-OBS-INJECTION-CONFIG`、§5.1 `IF-OBS-INJECT` "PATCH partial upsert；
副作用=注入配置写 + 审计"）；错误目录 `ERR-INJECTION`/`ERR-NOTFOUND`/`ERR-STORE`；需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01..06`、`CT-ADMIN-001`（[系统测试方案 §6 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）；
机器契约 [`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)（`InjectionList`/`InjectionWrite`/`InjectionView`）。
**不证明什么**：不证明注入对推理的**命中效果**（ST-RESP-011/22 在 B 类以真实 `POST /v1/responses` 证明 `fault_502`/`fault_503` 命中；本 case 只证明"配置写入并可由 GET 读回"）、不证明非法项 400（ST-OBSDEPL-004）、不证明未知 deployment 404（ST-OBSDEPL-003）、不证明别名等价（ST-OBSALIAS-004）。
**实现现状（已对齐 openapi）**：`InjectionList` openapi `required:["items"]`；handler 在 PATCH 前检查 `if "items" not in body: raise ApiError(400, "invalid_request", ...)`（`app.py:331-332` 扁平、`app.py:341-342` 别名），故缺 `items` 是 **400**，不会静默 revoke。
本 case 用规范 body。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=计划 §3 附加（B 类）；执行前附加（B 类）实例可用、`prov_b`+`depl_b`+7 tier、`depl_b` healthy、LAN fake provider；fixture：`llmtier_b` + `admin_client_b`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。初始状态=基线，`diagnostic_injections` **为空**（无启用注入）。**写 case：必须 teardown 清空**（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 3. 输入构造

- **输入与构造**：`PATCH /v1/deployments/depl_b/diagnostics`、`Authorization: Bearer dev-admin`、`Content-Type: application/json`。
  - 写入：`{"items": [{"type": "delay", "config": {"delay_ms": 2000}, "enabled": true}]}`
  - upsert 复核：再次 `PATCH` 同 `type` 改配置 `{"items": [{"type": "delay", "config": {"delay_ms": 500}, "enabled": true}]}` → 断言该 `type` 仅 1 项且 `delay_ms` 更新为 500（不新增重复项）。
  - 多类型：`{"items": [{"type":"fault_502","config":{"error_body":"boom"},"enabled":true},{"type":"rate_limit","config":{"retry_after_sec":2},"enabled":false}]}` → 断言两项、`enabled` 各自正确。
  - revoke：`{"items": []}` → 断言返回 `[]`（清空）。
  边界点：`delay_ms` 合法范围 `[0,60000]`；`enabled=false` 项被持久但不应生效（生效判定属 ST-RESP-011/22）；不构造非法项（ST-OBSDEPL-004）。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /v1/deployments/depl_b/diagnostics` → 断言初始 `[]`。
  2. `PATCH` 写入 `delay/delay_ms=2000/enabled=true` → 断言 `200`、body 数组含 `{type:"delay", config.delay_ms==2000, enabled:true, deployment_id:"depl_b"}`、恰 6 键、有 `id`/`updated_at`。
  3. `GET` 同路径 → 断言与步骤 2 一致（已持久化）。
  4. `PATCH` 同 `type` 改 `delay_ms=500` → 断言数组仍只 1 个 `delay` 项且 `delay_ms==500`（upsert 非新增）。
  5. `PATCH` 多类型（`fault_502` enabled=true、`rate_limit` enabled=false）→ 断言 2 项且各自 `enabled` 正确。
  6. （可选交叉证据）`GET /v1/audit` → 断言存在 `action=="diagnostics.injection.update"`、`target=="depl_b"`、`result=="success"` 的行。
  7. （teardown，`finally` 内）`PATCH` body `{"items": []}` → 断言 `200` 且 `[]`；`GET` 复核为空。

**重点关注步骤**：① **写入可读回**——步骤 3 的 `GET` 必须与 `PATCH` 返回一致，证明持久而非仅回显。② **upsert 幂等**——同 `type` 重复写只保留 1 项（`ON CONFLICT(deployment_id,injection_type) DO UPDATE`），不得追加重复。
③ **`enabled` 语义**——`enabled=false` 项仍持久（GET 可见）但不应生效；本 case 只断言持久。④ **项键集/枚举**——`InjectionView` 恰 6 键、`type` 白名单；`InjectionWrite` 恰 3 键。
⑤ **revoke 语义**——`{"items":[]}` 清空；**必须**在 `finally` 执行，绝不把启用注入留给同 session 的 ST-RESP-011/22 或后续 case。⑥ **缺 `items` 是 400**——handler 在 PATCH 前 `if "items" not in body: 400`（`app.py:331-332`/`341-342`），缺键不会静默 revoke；
本 case 用规范 body（缺键负向不在本 case 范围）。⑦ **同事务审计**——成功写入应可在 `GET /v1/audit` 见到；审计缺失即 FAIL。⑧ **降级/存储**——`_UnavailableDiagnostics.set_injections` 返回 `[]`（fail-open）；
健康实例断言以真实库为准；`503 usage_store_unavailable` 判 BLOCKED/SKIP。自动化入口 `ST-OBSDEPL-002.py` 已实现（§3.5 P0 Gate 阻断项已消解）。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `InjectionView[]`/`InjectionWrite` wire 形态 + 机制 §4.3.2/§5.1 upsert+审计保证。
  - `PATCH`：HTTP `200`；`Content-Type: application/json`；body 为 `InjectionView[]`（每项恰 6 键、`type` 枚举、`config` 对象、`enabled` 布尔、`deployment_id` 匹配）。
  - upsert：同 `(deployment_id,type)` 不产生重复项。
  - revoke：`{"items":[]}` → `200` + `[]`。
  - 审计（独立交叉证据）：`GET /v1/audit` 含 `diagnostics.injection.update` 成功行（`target=depl_b`）。
  - **fail-open**：降级实例 `set_injections` 返回 `[]` 且不写库——降级下无法证明写入契约，判 **BLOCKED/SKIP**，**不**把空数组当 PASS。`503 usage_store_unavailable` 判 **BLOCKED/SKIP**。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：写入 `200` 且 GET 可读回；同 type upsert 不重复；多类型/`enabled` 正确；审计存在；`finally` revoke 成功清空。
  - **FAIL**：任一断言不符——status 错、GET 读不回、重复项、`enabled` 错、审计缺失、或 teardown 未清空。
  - **BLOCKED**：测试代码/断言不可实现、降级实例、存储不可达——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：B 类实例不可用、依赖 fixture 未满足（含 `depl_b` 非 healthy）——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：无（自动化入口已实现；P0 Gate 阻断项已消解，执行状态见 Run 报告）。
  - **INVALID**：用 mock/替代路径冒充真实实例，或注入未真正写入却按行为判定——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。

## 6. 错误路径、副作用与清理

- **清理与复位**：**必须 teardown（`finally` 强制）**——`PATCH {"items":[]}` 清空，随后 `GET` 复核无启用项；不改 `prov_b`/`depl_b`、不重指 endpoint、不删除既有资源。离开前确认无未清空注入项；清空失败必须报错，不得留给后续 Case。 B 类整班结束由 fixture `stop()` + `rm -rf` 临时目录（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存初始 `GET`、每个 `PATCH` 请求/响应、upsert 前后对比、多类型项、`GET /v1/audit` 审计行、teardown `items:[]` 与最终 `GET`、命令/exit code/`elapsed`、环境快照（`/healthz` + 注入前/后 `GET /deployments/depl_b/diagnostics`）；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/B-api`，`environment:"b"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go)（B 类附加）；`llmtier_b`/`admin_client_b` fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；M007 `diagnostic_injections`；`InjectionList`/`InjectionWrite`/`InjectionView` 机器契约；实现 [`src/libdiag/injections.py`](../../../../src/libdiag/injections.py)、[`src/http_api/app.py`](../../../../src/http_api/app.py)（`app.admin.mutate` 同事务审计）。自动化入口 `ST-OBSDEPL-002.py`（已实现）。**不依赖**其它 Case；是 ST-RESP-011/22 的注入写入机制；与 ST-OBSDEPL-001/03/04、ST-OBSALIAS-004 语义相邻但各自独立执行。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
