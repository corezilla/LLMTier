<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-OBSALIAS-002 — 别名 diagnostics/snapshots

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-OBSALIAS-002` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-OBSALIAS-002.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`ST-OBSALIAS-002`）；责任摘要、分类与优先级以 [系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单) 清单行为准。
- **测试脚本的唯一依据**：编码者按本文档写测试代码，不需要回读方案或设计正文猜测意图。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-OBSALIAS-002` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-OBSALIAS-002` / 系统设计 §8 契约别名命名空间（/tier/admin/v1/*） / `VRC-DIAG-002` / `normal` / `P2`
- **测试方法（§1.5 方法表行）**：契约字段比对（别名/规范路由逐字节 parity）
- 方案清单登记：`ST-OBSALIAS-002`
- 要测什么（责任展开）：`/tier/admin/v1/diagnostics/snapshots` 与 `/v1/diagnostics/snapshots` 的 GET 由同一 handler 服务：status 与响应体逐字节等价。
- 明确不测什么 / 失败含义：不证明 快照内容/脱敏（ST-OBSSNAP-001）、不证明无效 cursor 负向（ST-OBSSNAP-002）、不证明 diagnostics/stats、traces 或 trace 别名（ST-OBSALIAS-005/06/03）、不证明别名鉴权负向（ST-AUTH-008）。

**目的（被测契约）**：验证快照查询别名的**逐字节等价契约**。被测端点/规则：`GET /tier/admin/v1/diagnostics/snapshots` 是 `/v1/diagnostics/snapshots` 的精确别名（openapi `x-llmtier-contract-aliases`：`"/tier/admin/v1/diagnostics/snapshots": "/v1/diagnostics/snapshots"`），同一 handler、相同 `SnapshotPage` 形状、相同 `admin` 鉴权（[`src/http_api/app.py`](../../../../src/http_api/app.py) 两分支调用同一 `app.diagnostics.snapshots_page`）；body 应逐字节等价（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。设计验证项 `VRC-DIAG-002`；机制 `T-TRUST-SHARED` + `T-OBS-SNAP`（[observability 机制](../../../20_system_design/mechanisms/observability.md) §5.1 `IF-OBS-API-QUERY`）；需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01..06`、`CT-ADMIN-001`（[系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）；机器契约 [`llmtier.openapi.json`](../../../../interfaces/openapi/llmtier.openapi.json)（`x-llmtier-contract-aliases`、`SnapshotPage`）。**不证明什么**：不证明快照内容/脱敏（ST-OBSSNAP-001）、不证明无效 cursor 负向（ST-OBSSNAP-002）、不证明 diagnostics/stats、traces 或 trace 别名（ST-OBSALIAS-005/06/03）、不证明别名鉴权负向（ST-AUTH-008）。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `admin_client`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；初始状态=§2.3 A 类基线；本 case 纯 GET，初态即终态。

## 3. 输入构造

- **输入与构造**：固定请求（无 body）：
  - `GET /v1/diagnostics/snapshots?limit=50`
  - `GET /tier/admin/v1/diagnostics/snapshots?limit=50`
  同凭据、同参数（可加相同 `since`/`until` 固定窗）。边界点：两请求参数必须**逐一相同**（否则 body 本可不同）；`X-Request-ID` 每次不同，**不参与** body 比较，也不列入 Oracle。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz`（§2.1，自动执行）。
  2. `GET /v1/diagnostics/snapshots?limit=50`（`admin_client`）→ 记录 status/`Content-Type`/原始 body。
  3. `GET /tier/admin/v1/diagnostics/snapshots?limit=50`（同 client、同参数）→ 记录同样字段。
  4. 断言两 `status == 200`、`Content-Type` 相同、`resp.content` **逐字节相等**。
  5. 断言两者均为合法 `SnapshotPage`（顶层键集恰 `{items, next_cursor, has_more}`）；本 case 仅判等价，形状细节归 ST-OBSSNAP-001。

**重点关注步骤**：① **参数严格对齐**——两请求 query 完全一致才可逐字节比较。② **逐字节 body 等价**——比较 `resp.content`，不是解析后对象。③ **只比 body**——`X-Request-ID` 不参与，也不列入 Oracle。④ **鉴权等价**——都需 `admin`（本 case 正向；负向 ST-AUTH-008）。⑤ **空页也须等价**——`items=[]` 时两路径仍应完全一致。⑥ **降级/存储**——降级实例两路径同样返回空页（等价仍成立，判 BLOCKED/SKIP 说明语义）；`503 usage_store_unavailable` 判 BLOCKED/SKIP。自动化入口 `at_obs_alias_02.py` 已实现。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = openapi `x-llmtier-contract-aliases` 的同一 handler/相同形状 + `SnapshotPage` wire 形态。
  - 两路径均 `200`，`Content-Type: application/json`，`body_flat == body_alias`（逐字节）。
  - 均为合法 `SnapshotPage`。
  - **fail-open**：降级实例两路径同样空页（等价成立）；`503 usage_store_unavailable` 判 **BLOCKED/SKIP**；body 不等价 → **FAIL**。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：两路径 status 相同且 body 逐字节相等（含空页）。
  - **FAIL**：status/body 不等价或别名 404。
  - **BLOCKED**：测试代码/契约问题、降级实例、存储不可达——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：无（自动化入口已实现；执行状态见 Run 报告）。
  - **INVALID**：用 `127.0.0.1`/mock/替代路径冒充真实 m5air，或未真正比较两路径却按等价判定——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——纯读。退出前确认 `/readyz` 仍 7 tier、无未清空注入项。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存两路径响应与逐字节对比、命令/exit code/`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 6 项就绪检查；`admin_client` fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）；openapi `x-llmtier-contract-aliases`；实现 [`src/http_api/app.py`](../../../../src/http_api/app.py)（`/tier/admin/v1/diagnostics/snapshots` 分支）。自动化入口 `at_obs_alias_02.py`（已实现）。**不依赖**其它 Case；与 ST-OBSSNAP-001（内容/脱敏）、ST-AUTH-008（别名鉴权）语义相邻，与其它别名并列但各自独立执行。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
