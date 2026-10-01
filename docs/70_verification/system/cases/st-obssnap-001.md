<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-obssnap-001 — 快照页（脱敏）

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-obssnap-001` |
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
| Canonical Path | `docs/70_verification/system/cases/st-obssnap-001.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`ST-obssnap-001`）；责任摘要、分类与优先级以 [系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单) 清单行为准。
- **测试脚本的唯一依据**：编码者按本文档写测试代码，不需要回读方案或设计正文猜测意图。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-obssnap-001` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-obssnap-001` / 系统设计 §8 诊断快照接口（/v1/diagnostics/snapshots） / `VRC-DIAG-002` / `normal` / `P1`
- **测试方法（§1.5 方法表行）**：等价类划分 + 契约字段比对
- 方案清单登记：`ST-obssnap-001`
- 要测什么（责任展开）：`GET /v1/diagnostics/snapshots` 返回 `SnapshotPage`：`{items[], next_cursor, has_more}` 键集精确、每项为恰好 11 键的 `SnapshotView`，且内容**已脱敏**（`upstream_url` 去 query、`error_summary` ≤256B、不含 Secret/凭据/正文）。
- 明确不测什么 / 失败含义：不证明 非法 cursor 的 400（ST-obssnap-002）、不证明快照**写入**开关门控（`capture_snapshot` 受 `snapshots_enabled` 控制，属机制 `INV-4`/`CON-OBS-001` 与 ST-obsdiag-002 的开关写入，本 case 只读现有页）、不证明统计/trace（ST-obsstats-001、ST-obstrace-001）、不证明别名等价（ST-obsalias-002）。

**目的（被测契约）**：验证 Observability `GET /v1/diagnostics/snapshots` 的**只读分页 + 脱敏契约**。被测端点/规则：`GET /v1/diagnostics/snapshots`（可选 `since`/`until`/`deployment_id`/`model`/`limit`/`cursor`），返回 `SnapshotPage`（`items`/`next_cursor`/`has_more` 三键必填）；每项 `SnapshotView` 必填 11 键（`id, request_id, captured_at, upstream_url, backend_model, http_status, latency_ms, error_summary, model, deployment_id, snapshot_type`），`snapshot_type ∈ {upstream,error}`；`upstream_url` "去 query"、`error_summary` ≤256B、`http_status ∈ [100,599]|null`、`latency_ms ≥0|null`；认证角色 `admin`；失败走统一信封 `{error:{message,type,code,param,retryable}}`（401/403/503）。设计验证项 `VRC-DIAG-002`；机制 `T-OBS-SNAP`（[observability 机制](../../../20_system_design/mechanisms/observability.md) §4.2 `D-OBS-SNAPSHOT`、§4.9 `D-OBS-SNAPSHOT` 映射、§4.10、`CON-OBS-003` 不记录 Secret/credential/完整正文）；错误目录 `ERR-STORE` → `usage_store_unavailable`（503）；需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01..06`、`CT-ADMIN-001`/`CT-LOG-001`（[系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）；机器契约 [`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)（`SnapshotPage`/`SnapshotView`，`security=AdminBearerAuth`）。**不证明什么**：不证明非法 cursor 的 400（ST-obssnap-002）、不证明快照**写入**开关门控（`capture_snapshot` 受 `snapshots_enabled` 控制，属机制 `INV-4`/`CON-OBS-001` 与 ST-obsdiag-002 的开关写入，本 case 只读现有页）、不证明统计/trace（ST-obsstats-001、ST-obstrace-001）、不证明别名等价（ST-obsalias-002）。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `admin_client`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；初始状态=§2.3 A 类基线；`diagnostic_settings` 默认 `snapshots_enabled=false`，故若从未开启过快照，`items` 可能为空——**本 case 为形状/脱敏断言，不以非空为 PASS 前提**。本 case 纯读，初态即终态。

## 3. 输入构造

- **输入与构造**：固定请求（无 body，可选时间窗）：
  `GET /v1/diagnostics/snapshots?limit=50`（如需限定数据可加 `?since=<RFC3339>&until=<RFC3339>`；`limit∈[1,500]`），`Authorization: Bearer dev-admin`、`Accept: application/json`。边界点：**无请求体**；`limit` 取默认 50（不触 `limit=1` 分页，属 ST-obssnap-002）；不构造非法 cursor（ST-obssnap-002）；不写入、不注入；`items` 是否非空不固定，只断言页与项形状及脱敏不变量。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz`（§2.1，由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `GET /v1/diagnostics/snapshots?limit=50`（`admin_client`）→ 记录 status、`Content-Type`、原始 body。
  3. 断言 `resp.status_code == 200` 且 `content-type` 含 `application/json`。
  4. 解析 JSON，断言顶层键集**恰为** `{items, next_cursor, has_more}`；`items` 为数组、`has_more` 为 JSON 布尔、`next_cursor` 为字符串或 `null`。
  5. 对每个 `item`：断言键集**恰为** `SnapshotView` 11 键；`id`/`request_id`/`captured_at`/`upstream_url` 为字符串；`backend_model`/`model`/`deployment_id` 为字符串或 `null`；`http_status` 为 `null` 或在 `[100,599]`；`latency_ms` 为 `null` 或 ≥0；`error_summary` 为 `null` 或字符串且 UTF-8 长度 ≤256；`snapshot_type ∈ {"upstream","error"}`。
  6. **脱敏断言**：逐项扫描 `upstream_url`（不得含 `?` 后 query 串）、`error_summary`、以及整段原始 body：不得出现上游凭据字面 `9832`、`Authorization`、`Bearer `、key 文件内容或任何 secret 值。
  7. （交叉核对，不改变判定）若 `items` 非空，取末条 `id` 作为 `cursor` 重放 `GET ...&cursor=<id>`，确认只读分页可用；本 case 不承担 cursor 负向判定。

**重点关注步骤**：① **页键集精确**——恰 3 键（`items`/`next_cursor`/`has_more`），多/少即违反；② **项键集精确**——每项恰 11 键，`additionalProperties:false`；③ **`snapshot_type` 枚举**——只允许 `upstream`/`error`（`upstream⇒http_status` 非空、`error⇒http_status` 空是机制 §4.2 不变量，可作交叉核对）；④ **`upstream_url` 去 query**——必须已剥离 `?` 后部分，这是 `D-OBS-SNAPSHOT` 的明确映射约束；⑤ **`error_summary` ≤256B**——按 UTF-8 截断，不得 >256；⑥ **脱敏不变量**——整段 body 不得含 `9832`/`Authorization`/secret；⑦ **空页合法**——`snapshots_enabled=false` 时 `items=[]` 仍是合法 `SnapshotPage`（形状 PASS），**不得**因空而判 FAIL；⑧ **降级/存储**——`_UnavailableDiagnostics.snapshots_page` 恒返回 `{items:[],next_cursor:null,has_more:false}` 的 **200**（fail-open，形状 PASS）；`503 usage_store_unavailable` 判 BLOCKED/SKIP。自动化入口 `at_obs_snap_01.py` 已实现（构造非空数据后断言项级/脱敏；落位遵循 §4.9/§8.5）。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `SnapshotPage`/`SnapshotView` wire 形态 + 机制 §4.2/§4.9 脱敏映射（不依赖实现内部）。
  - HTTP：`200`；`Content-Type: application/json`（openapi 未为 200 声明响应头）。
  - body：`{"items":[...], "next_cursor": <string|null>, "has_more": <bool>}`，键集恰 3。
  - 项：键集恰为 11 键；类型/范围/枚举如上；`upstream_url` 无 query；`error_summary` ≤256B。
  - 脱敏：任何字段与整段响应均不含 Secret/凭据/上游 Bearer/完整正文。
  - **fail-open**：降级实例返回 `200` + 空 `SnapshotPage`，形状仍满足 Oracle → **PASS**（观测降级不得制造新失败面，且本 case 不要求非空）；若健康实例返回非 200、或页/项键集不符、或出现未脱敏内容 → **FAIL**；`503 usage_store_unavailable` 判 **BLOCKED/SKIP**。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`200` + 页键集恰 3 + 每项恰 11 键且类型/范围/枚举正确 + `upstream_url` 去 query + `error_summary` ≤256B + 无未脱敏内容（含降级空页 fail-open）。
  - **FAIL**：非 200（存储健康时）、页/项键集不符、`snapshot_type` 越枚举、`upstream_url` 含 query、`error_summary` >256B、或响应含 Secret/凭据。
  - **BLOCKED**：测试代码/契约问题（解析器/断言逻辑错、openapi 语义不清）或存储不可达 `503 usage_store_unavailable`——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足（m5air/双 OMLX 离线、tier 或资源缺失）——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：无（自动化入口已实现；执行状态见 Run 报告）。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air，或未命中真实诊断服务却按行为判定——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——纯读，不写 `diagnostic_snapshots`、不改开关、不创建/修改资源、不写注入、不新增 trace。退出前确认无未清空注入项、`/readyz` 仍 7 tier。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存原始 HTTP status/headers/body、发出命令、exit code、`elapsed`、环境快照、`redactions`（确认 `Authorization` 与任何上游 Bearer 已脱敏）；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 6 项就绪检查；`admin_client` fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）；M007 `diagnostic_snapshots`（`002_observability.sql`）；`SnapshotPage`/`SnapshotView` 机器契约；实现 [`src/libdiag/snapshots.py`](../../../../src/libdiag/snapshots.py)、[`src/http_api/app.py`](../../../../src/http_api/app.py)。自动化入口 `at_obs_snap_01.py`（已实现）。**不依赖**其它 Case；与 ST-obssnap-002（无效 cursor 负向）、ST-obsdiag-002（开关写）语义相邻但各自独立执行。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
