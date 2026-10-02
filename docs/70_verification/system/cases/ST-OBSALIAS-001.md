<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-OBSALIAS-001 — 别名 diagnostics（GET+PATCH）

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-OBSALIAS-001` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-OBSALIAS-001.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`ST-OBSALIAS-001`）；责任摘要、分类与优先级以 [系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单) 清单行为准。
- **测试脚本的唯一依据**：编码者按本文档写测试代码，不需要回读方案或设计正文猜测意图。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-OBSALIAS-001` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-OBSALIAS-001` / 系统设计 §8 契约别名命名空间（/tier/admin/v1/*） / `VRC-DIAG-001` / `normal` / `P1`
- **测试方法（§1.5 方法表行）**：契约字段比对（别名/规范路由逐字节 parity）
- 方案清单登记：`ST-OBSALIAS-001`
- 要测什么（责任展开）：`/tier/admin/v1/diagnostics` 与 `/v1/diagnostics` 的 GET/PATCH 由同一 handler 服务：status 与响应体逐字节等价。
- 明确不测什么 / 失败含义：不证明 正常/非法开关语义本身（ST-OBSDIAG-001/02/03 分别在扁平路径断言）、不证明其它 5 条别名（ST-OBSALIAS-002..06）、不证明别名鉴权负向（ST-AUTH-008，本 case 用 admin 正向）、不证明错误路径在别名上的等价（本 case 以成功路径为主，404/400 等价可作旁证）。

**目的（被测契约）**：验证契约别名命名空间的**逐字节等价契约**。被测端点/规则：`GET`+`PATCH /tier/admin/v1/diagnostics` 是 `/v1/diagnostics` 的**精确别名**（openapi `x-llmtier-contract-aliases`：`"/tier/admin/v1/diagnostics": "/v1/diagnostics"`），同一 handler、相同请求/响应形状、相同 `admin` 鉴权（[`src/http_api/app.py`](../../../../src/http_api/app.py) 两分支调用同一 `app.diagnostics.switches/set_switches`）；
body 应逐字节等价（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；认证 `admin`。设计验证项 `VRC-DIAG-001`；机制 `T-TRUST-SHARED`（同一 handler 别名，[access-trust 机制](../../../20_system_design/mechanisms/access-trust.md)）+ `T-OBS-SWITCH`；
需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01..06`、`CT-ADMIN-001`（[系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）；
机器契约 [`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)（`x-llmtier-contract-aliases`、`SwitchState`、`DiagnosticsSwitchPatch`）。
**不证明什么**：不证明正常/非法开关语义本身（ST-OBSDIAG-001/02/03 分别在扁平路径断言）、不证明其它 5 条别名（ST-OBSALIAS-002..06）、不证明别名鉴权负向（ST-AUTH-008，本 case 用 admin 正向）、不证明错误路径在别名上的等价（本 case 以成功路径为主，404/400 等价可作旁证）。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；PATCH 属**一次性无状态写**，必须 teardown 恢复；fixture `admin_client`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；初始状态=§2.3 A 类基线；`diagnostic_settings` 单行（默认 `{false,false}`）。**写 case：PATCH 后必须恢复原开关值**（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 3. 输入构造

- **输入与构造**：
  - **GET 等价**：`GET /v1/diagnostics` 与 `GET /tier/admin/v1/diagnostics`，同凭据。
  - **PATCH 等价**：选定 body `B = {"snapshots_enabled": <取反原值 or true>, "stats_enabled": <原值>}`；先 `PATCH /v1/diagnostics` body `B`，再 `PATCH /tier/admin/v1/diagnostics` body 同为 `B`（幂等，二次同值应用后终态相同）；比较两次返回体。
  - 边界点：`SwitchState` 返回无时间戳，PATCH 幂等，故二次同值 body 的返回**应逐字节相等**（与 ST-OBSALIAS-004 含 `updated_at` 的情形不同）；`X-Request-ID` 每次不同，**不参与** body 比较，也不列入 Oracle。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /v1/diagnostics`（`admin_client`）→ 记录 `orig_raw`（原始字节）与解析值。
  2. `GET /tier/admin/v1/diagnostics`（同 client）→ 记录 status/body；断言 `status` 相同、`resp.content == flat_resp.content`（逐字节）。
  3. `PATCH /v1/diagnostics` body `B` → 记录 `patch_flat`（status/body）。
  4. `PATCH /tier/admin/v1/diagnostics` body 同 `B` → 记录 `patch_alias`；断言 `patch_alias.status_code == patch_flat.status_code == 200` 且 `patch_alias.content == patch_flat.content`（逐字节；`SwitchState` 无服务端时间戳，同值幂等）。
  5. （旁证）`GET /v1/diagnostics` 与别名 GET 再比对一次（确认 PATCH 后仍等价）。
  6. （teardown，`finally` 内）`PATCH /v1/diagnostics` body `{"snapshots_enabled": orig.snapshots_enabled, "stats_enabled": orig.stats_enabled}` → 200；`GET` 校验回到 `orig_raw`。

**重点关注步骤**：① **逐字节 body 等价**——GET 与 PATCH 均须 `content` 相同；仅"schema 相同"不够。② **只比 body，不比 header**——`X-Request-ID` 每次请求不同，**不得**把响应头纳入逐字节断言，也不得列入 Oracle（openapi 未声明 200 头）。
③ **鉴权等价**——两条路径都需 `admin`；本 case 以 `dev-admin` 正向，负向（data → 403）由 ST-AUTH-008 承接。④ **幂等 PATCH**——两次同值 body 的返回应相等；不得因 `updated_at`/审计导致 body 差异（`SwitchState` 不含这些字段）。
⑤ **teardown 完整性**——`finally` 恢复原值并字节校验，绝不把开关留在非初态影响 OBS-SNAP/STATS。⑥ **降级/存储**——`_UnavailableDiagnostics` 下两条路径仍同 handler、应同样返回默认，等价断言仍可做（但无法证明真实开关语义，判 BLOCKED/SKIP）；
`503 usage_store_unavailable` 判 BLOCKED/SKIP。自动化入口 `ST-OBSALIAS-001.py` 已实现。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = openapi `x-llmtier-contract-aliases` 的"同一 handler、相同请求/响应形状" + `SwitchState` wire 形态。
  - GET：两路径 `200`，`Content-Type: application/json`，`body_flat == body_alias`（逐字节）。
  - PATCH：两路径 `200`，body 均为合法 `SwitchState`（键集恰 `{snapshots_enabled, stats_enabled}`），且 `body_flat == body_alias`（逐字节）。
  - teardown：恢复后 GET 等于 `orig_raw`。
  - **fail-open**：降级实例两路径同样返回默认（等价仍成立但语义需 BLOCKED/SKIP 说明）；`503 usage_store_unavailable` 判 **BLOCKED/SKIP**；body 不等价 → **FAIL**。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：GET 与 PATCH 的扁平/别路径 status 相同且 body 逐字节相等；teardown 恢复原值成功。
  - **FAIL**：status 或 body 不等价、别名 404/非同一 handler、或 teardown 未恢复。
  - **BLOCKED**：测试代码/契约问题、降级实例、存储不可达——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：无（自动化入口已实现；执行状态见 Run 报告）。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air，或未真正比较两路径却按等价判定——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。

## 6. 错误路径、副作用与清理

- **清理与复位**：**必须 teardown（`finally` 强制）**——PATCH 恢复 `(orig_snapshots, orig_stats)` 并二次 GET 校验；不创建/删除资源、不写注入。退出前确认开关初值、`/readyz` 7 tier、无未清空注入项。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存两路径 GET body、两路径 PATCH 请求/响应、逐字节对比结果、teardown 与恢复校验、命令/exit code/`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 6 项就绪检查；`admin_client` fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）；openapi `x-llmtier-contract-aliases`；实现 [`src/http_api/app.py`](../../../../src/http_api/app.py)（`/v1/diagnostics` 与 `/tier/admin/v1/diagnostics` 分支）。自动化入口 `ST-OBSALIAS-001.py`（已实现）。**不依赖**其它 Case；与 ST-AUTH-008（别名需 admin）语义相邻，与 ST-OBSALIAS-002..06 并列但各自独立执行。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
