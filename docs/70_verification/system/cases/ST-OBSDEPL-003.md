<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-OBSDEPL-003 — 注入未知 deployment

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-OBSDEPL-003` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-OBSDEPL-003.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本文档只展开一个 Case；Document ID＝Case ID（`ST-OBSDEPL-003`）；责任摘要、分类与优先级以 [系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单) 清单行为准。
- **测试脚本的唯一依据**：编码者按本文档写测试代码，不需要回读方案或设计正文猜测意图。
- **不预填结果**：本文档持有实现状态；执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-OBSDEPL-003` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-OBSDEPL-003` / 系统设计 §8 注入配置接口（/v1/deployments/{id}/diagnostics） / `VRC-DIAG-004` / `negative` / `P1`
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（ERR-*）
- 方案清单登记：`ST-OBSDEPL-003`
- 要测什么（责任展开）：`PATCH /v1/deployments/{id}/diagnostics` 对未知 deployment：HTTP 404 `not_found`，不写入任何注入行。
- 明确不测什么 / 失败含义：不证明 正向写入（ST-OBSDEPL-002）、不证明非法注入项的 400（ST-OBSDEPL-004）、不证明 GET 读取侧未知 404（虽同实现检查，本 case 聚焦 PATCH；可将 GET 作为交叉核对）、不证明别名等价（ST-OBSALIAS-004）。

**目的（被测契约）**：验证注入写路径的**资源存在性负向契约**。被测端点/规则：`PATCH /v1/deployments/{deployment_id}/diagnostics`，`set_injections` 首先 `SELECT 1 FROM deployments WHERE id=?`，不存在则抛 `ApiError(404, "not_found", "Unknown deployment: <id>")`（[`src/libdiag/injections.py`](../../../../src/libdiag/injections.py)），**先于**对 `items` 的校验；因此即使 body 为 `{"items":[]}` 或含非法项，未知 deployment 也应是 404（存在性优先）；**零副作用**（不写注入、不写成功审计；`mutate` 失败路径记 `result="failed"`）。设计验证项 `VRC-DIAG-004`；机制 `T-OBS-INJECT`（[observability 机制](../../../20_system_design/mechanisms/observability.md) §5.1 `IF-OBS-INJECT` "未知 deployment（读）→ `ERR-NOTFOUND`（404）；校验失败不写、副作用无"）；错误目录 `ERR-NOTFOUND` → `not_found`（[系统设计 §7.8](../../../20_system_design/llmtier-system-design.md)，见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理) `ERR-NOTFOUND → ...、ST-OBSDEPL-003、...`）；需求链 `LT-FUN-005`/`LT-OPS-006`/`LT-INT-007`、`R-OBS-01..06`、`CT-ADMIN-001`（[系统测试方案 §3 覆盖分母与 Case 清单](../llmtier-system-test-scheme.md#3-覆盖分母与-case-清单)）。**不证明什么**：不证明正向写入（ST-OBSDEPL-002）、不证明非法注入项的 400（ST-OBSDEPL-004）、不证明 GET 读取侧未知 404（虽同实现检查，本 case 聚焦 PATCH；可将 GET 作为交叉核对）、不证明别名等价（ST-OBSALIAS-004）。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 附加（B 类）；执行前附加（B 类）；fixture：`llmtier_b` + `admin_client_b`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。初始状态=基线；本 case 期望零写入、**不存在**该 deployment；结束再次确认库中无该 id 的注入。

## 3. 输入构造

- **输入与构造**：固定请求：
  `PATCH /v1/deployments/does_not_exist/diagnostics`、`Authorization: Bearer dev-admin`、`Content-Type: application/json`，body 逐项独立发起：
  - `{"items": [{"type": "delay", "config": {"delay_ms": 1000}, "enabled": true}]}`（合法注入项但未知 deployment）
  - `{"items": []}`（revoke 形态但未知 deployment——验证存在性优先于"空列表清空"）
  - `{"items": [{"type": "bogus", "config": {}, "enabled": true}]}`（非法 type + 未知 deployment——验证 404 优先于 400）
  - `{"items": "not-a-list"}`（非数组 + 未知 deployment）

  边界点：`{id}` 为语法合法但库中不存在的字符串（如 `dep_deadbeef`）；不测已存在 deployment（ST-OBSDEPL-002）。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /v1/deployments/does_not_exist/diagnostics`（交叉核对）→ 断言 `404 not_found`（同存在性检查）。
  2. 对每个 PATCH body 变体 `PATCH` → 断言 `resp.status_code == 404`。
  3. 每次取 `err = resp.json()["error"]`：断言键集恰 5、`err["code"]=="not_found"`、`err["type"]=="request_error"`、`err["retryable"] is False`。
  4. 断言 body `{"items":[]}` 在该未知 id 上返回 **404 而非 200**（存在性优先于清空语义）。
  5. 断言 body 含非法 type 时返回 **404 而非 400**（存在性优先于项校验）——若返回 400 则存在性检查顺序错误，判 FAIL（与 `set_injections` 的顺序契约不符）。
  6. （可选交叉证据）`GET /v1/audit` → 断言存在 `result=="failed"` 的 `diagnostics.injection.update` 行，且无成功行。

**重点关注步骤**：① **存在性优先顺序**——`set_injections` 先查 deployment 再校验 items；故未知 deployment + 非法项 → 404（不是 400），未知 deployment + `items:[]` → 404（不是 200 清空）。这是本 case 最易误判点。② **code 精确**——`not_found`（非 `invalid_injection`/`invalid_request`）。③ **零副作用**——404 不写注入行、不写成功审计。④ **错误信封 identity**——恰 5 键、`type=request_error`。⑤ **GET/PATCH 一致**——读与写都做存在性检查，404 语义一致。⑥ **失败审计**——`mutate` 失败路径记 `result="failed"`。⑦ **降级/存储**——`_UnavailableDiagnostics.set_injections` 返回 `[]`（不检查存在性）属降级实例 → BLOCKED/SKIP；`503 usage_store_unavailable` 判 BLOCKED/SKIP。自动化入口 `at_obs_depl_03.py` 已实现。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `NotFound`（`ErrorEnvelope`）+ 机制 §5.1 存在性检查顺序语义。
  - `PATCH` 未知 deployment（任意 body 变体）：HTTP `404`；`Content-Type: application/json`；body `{"error":{"message":"Unknown deployment: does_not_exist","type":"request_error","code":"not_found","param":<string|null>,"retryable":false}}`（恰 5 键；`message` 措辞以实现为准，仅断言 code/type）。
  - 交叉：`GET` 同未知 id → `404 not_found`。
  - 零副作用：库中无该 id 的注入行。
  - **fail-open**：降级实例不检查存在性、返回空（无法证明契约）→ **BLOCKED/SKIP**；健康实例返回 400/200 而非 404 → **FAIL**；`503 usage_store_unavailable` 判 **BLOCKED/SKIP**。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：所有未知 id PATCH（含 `items:[]`、非法项、非数组）均 `404 + not_found`，且 GET 一致、零副作用。
  - **FAIL**：返回 200/400 而非 404、`code` 不符，或出现注入写入。
  - **BLOCKED**：测试代码/契约问题、降级实例、存储不可达——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：B 类实例不可用、依赖 fixture 未满足——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：无（自动化入口已实现；执行状态见 Run 报告）。
  - **INVALID**：用 mock/替代路径冒充真实实例，或未真正提交未知 id 却按行为判定——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需数据 teardown**——未知 id 零写入；确认库中无该 id 注入行。离开前确认无残留、`/readyz` 7 tier、无未清空注入项。 B 类整班结束由 fixture `stop()` + `rm -rf` 临时目录（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存每个 body 变体的原始 404 信封、GET 交叉 404、失败审计（可选）、命令/exit code/`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/B-api`，`environment:"b"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go)（B 类附加）；`llmtier_b`/`admin_client_b` fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）；`ERR-NOTFOUND`；实现 [`src/libdiag/injections.py`](../../../../src/libdiag/injections.py)、[`src/http_api/app.py`](../../../../src/http_api/app.py)。自动化入口 `at_obs_depl_03.py`（已实现）。**不依赖**其它 Case；与 ST-OBSDEPL-002（正向写）、ST-OBSDEPL-004（非法项）互补且需注意判定顺序差异，各自独立执行。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
