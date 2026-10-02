<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-SL-004 — 更新 service-level

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-SL-004` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-SL-004.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-SL-004`）；责任摘要、分类与优先级以 [系统测试方案 §3](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 Service Level CRUD 接口（/v1/service-levels）（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-002`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-SL-004` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-SL-004` / 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） / `VRC-MGMT-002` / `concurrency` / `P1`
- **测试方法（§1.5 方法表行）**：状态机驱动（If-Match/412 串行化）+ 固定并发度/种子 + 契约字段比对
- 方案清单登记：`ST-SL-004`（与 §3.2 权威清单一致；本文件名 `st-sl-004.md`，唯一对应）。
- 要测什么（责任展开）：`PATCH /v1/service-levels/{id}` 携带正确 `If-Match` 切换 `enabled`：HTTP 200 + 字段生效 + `version`/`ETag` 推进。
- 明确不测什么 / 失败含义：不证明 非法字段 400（ST-SL-013）、不证明成员能力/向量空间冲突 409（ST-SL-006/07）、不证明删除 409（ST-SL-005）、不证明缺/过期 `If-Match` 412（未单独构 SL 的 412 Case，语义同 ST-PROV-006/07）、不证明并发两写者竞争（[测试设计 §5](../llmtier-system-test-scheme.md) 不单独构 case）。

**目的（被测契约）**：验证 Service Level 的**乐观并发更新契约**。被测端点/规则：`PATCH /v1/service-levels/{service_level_id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `updateServiceLevel`，body `ServiceLevelPatch`=`{deployment_ids?
,enabled?}` 且 `minProperties:1`，`additionalProperties:false`；header `If-Match` 必填），[`registry.update_service_level`](../../../../src/management/registry.py) 仅接受 `deployment_ids`/`enabled`，`If-Match` 必须等于当前 ETag `"<id>.v<N>"`，成功 `200` + 新 `ServiceLevelView` + `ETag: "<id>.v<N+1>"`。
设计验证项 `VRC-MGMT-002`；机制 `T-CFG-CAS`；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`CT-ADMIN-001`。**不证明什么**：不证明非法字段 400（ST-SL-013）、不证明成员能力/向量空间冲突 409（ST-SL-006/07）、不证明删除 409（ST-SL-005）、不证明缺/过期 `If-Match` 412（未单独构 SL 的 412 Case，语义同 ST-PROV-006/07）、不证明并发两写者竞争（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理) 不单独构 case）。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 附加（B 类）；fixture `admin_client_b`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；初始状态=`Junior` 存在且 `enabled=true`、`deployment_ids=["depl_b"]`。

## 3. 输入构造

- **输入与构造**：
  ```http
  PATCH /v1/service-levels/Junior HTTP/1.1
  Host: 127.0.0.1:<port>
  Authorization: Bearer dev-admin
  If-Match: "<从 GET 读取的真实 ETag>"
  Content-Type: application/json
  ```
  ```json
  {"enabled": false}
  ```
  构造点：先 `GET /v1/service-levels/Junior` 取 `original_etag`（**绝不硬编码 `"Junior.v1"`**）；PATCH body 只含 `enabled`（`additionalProperties:false`，`enabled` 为 bool）。不注入故障。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `get = admin_client_b.get("/v1/service-levels/Junior")`；断言 200；记 `original_etag = get.headers["ETag"]`、`original_version = body["version"]`；断言 `body["enabled"] is True`。
  3. `patch = admin_client_b.patch("/v1/service-levels/Junior", json={"enabled":False}, headers={"If-Match": original_etag})`。
  4. 断言 `patch.status_code == 200`；`updated = patch.json()`：`enabled is False`、`version > original_version`（期望 `+1`）；`patch.headers` 含 `ETag`。
  5. （teardown，`finally` 内）重新 `GET` 取当前 ETag（版本可能已推进），若 `enabled is not True` 则 PATCH `{"enabled": True}` 复位；断言复位后 `enabled is True`。

**重点关注步骤**：① **真实 ETag**——必须取自刚做的 `GET` 响应头；硬编码版本会在创建/并发后失效；② **版本推进**——`version` 必 `+1` 且新 ETag `"Junior.v<N+1>"` 与之一致；
③ **字段生效**——`enabled` 回显更新值，`deployment_ids`/`capabilities` 未提交字段保持原值（PATCH 是合并语义，[`update_service_level`](../../../../src/management/registry.py) 用 `current_ids`）；
④ **412 恢复**——若因并发得 412，须重新 `GET` 取新 ETag 再 PATCH，不覆盖式重发（本 case 正常路径不触发）；⑤ **teardown 到位**——复位必须用最新 ETag；复位后不得把后续 Case 置于 `enabled=false` 状态（`enabled=false` 会使 `registry.candidates` 返回空，影响路由类 Case）。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ServiceLevelPatch`/`ServiceLevelView` + ETag/CAS 规则。
  - PATCH：`200`；body `enabled is False`、`version == original+1`；响应头 `ETag == "Junior.v<original+1>"`。
  - 回读：`GET` → 200，`enabled` 持久化为 false。
  - teardown：PATCH 复位 → 200，`enabled is True`。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：PATCH `200` + `enabled` 生效 + `version` 推进 + 新 ETag 一致；teardown 成功复位为 true。
  - **FAIL**：status 错、`version` 未推进、`enabled` 未生效、ETag 不符、或 teardown 未复位。
  - **BLOCKED**：fixture/断言逻辑问题——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：B 类临时实例不可用——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：硬编码/伪造 ETag 绕过真实 `GET` 语义，或用 `127.0.0.1` 作上游 endpoint——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**必须 teardown（`finally` 强制）**——把 `Junior.enabled` 恢复为 `true`（用最新 ETag）；不改其它 tier、不删资源、不写注入。退出前确认 `GET /v1/service-levels/Junior` 的 `enabled is True`、`/readyz` 仍 ready。 B 类整班结束由 fixture `stop()` + `rm -rf` 临时目录（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存GET/PATCH/复位 PATCH 的请求与原始响应（含 `If-Match`/`ETag` 头，脱敏后）、发出命令、exit code、`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/B-api`，`environment:"b"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）；`ServiceLevelPatch`/`ServiceLevelView` 机器契约；`registry.update_service_level`/`_etag`；机制 `T-CFG-CAS`。自动化入口 [`ST-SL-004.py`](../../../../tests/system/cases/ST-SL-004.py)。**不依赖**其它 Case；与 ST-SL-013（非法字段 400）互补但各自独立执行。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
