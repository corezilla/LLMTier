<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-SL-003 — 获取 service-level

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-SL-003` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-SL-003.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-SL-003`）；责任摘要、分类与优先级以 [系统测试方案 §3](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 Service Level CRUD 接口（/v1/service-levels）（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-002`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-SL-003` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-SL-003` / 系统设计 §8 Service Level CRUD 接口（/v1/service-levels） / `VRC-MGMT-002` / `normal` / `P0`
- **测试方法（§1.5 方法表行）**：等价类划分 + 契约字段比对
- 方案清单登记：`ST-SL-003`（与 §3.2 权威清单一致；本文件名 `st-sl-003.md`，唯一对应）。
- 要测什么（责任展开）：`GET /v1/service-levels/{id}` 精确返回单个固定 Tier：HTTP 200 + `ServiceLevelView` + `ETag`。
- 明确不测什么 / 失败含义：不证明 列表（ST-SL-001）、不证明更新/删除（ST-SL-004/04b/05/06/07/08）、不证明不存在 id 的 404（未单独构 case；由 `registry.get_service_level` 的 `not_found` 语义承载）、不证明 If-Match/CAS（ST-SL-004）。

**目的（被测契约）**：验证 Service Level **单条详情读契约**。被测端点/规则：`GET /v1/service-levels/{service_level_id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `getServiceLevel`，路径参数 `service_level_id`，`security=AdminBearerAuth`），成功 `200` + `ServiceLevelView`（`{id,deployment_ids,enabled,capabilities,version}`，`additionalProperties:false`）+ 响应头 `ETag: "<id>.v<N>"`（[`registry.get_service_level`](../../../../src/management/registry.py) 返回 `_etag`）。设计验证项 `VRC-MGMT-002`；需求/机制链 `LT-FUN-005`、`R-CFG-01`、`CT-ADMIN-001`。**不证明什么**：不证明列表（ST-SL-001）、不证明更新/删除（ST-SL-004/04b/05/06/07/08）、不证明不存在 id 的 404（未单独构 case；由 `registry.get_service_level` 的 `not_found` 语义承载）、不证明 If-Match/CAS（ST-SL-004）。

## 2. 被测入口与前置

- **前置与环境**：**环境 A**（m5air 已部署实例，角色 `admin`，只读；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；前置=§2.1 就绪检查（A 类 6 项，`pytest_configure` 自动执行，任一失败→整班 BLOCKED/SKIP）；fixture `admin_client`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；初始状态=§2.3 A 类基线（7 fixed tier）。本 case 选 `Worker`（responses-capable 固定 Tier，A 类必在）。

## 3. 输入构造

- **输入与构造**：固定请求：
  ```http
  GET /v1/service-levels/Worker HTTP/1.1
  Host: 192.168.1.9:8181
  Authorization: Bearer dev-admin
  Accept: application/json
  ```
  构造点：`{id}="Worker"` 精确大小写匹配 `FIXED_TIERS`（大小写敏感）；无 body、无 query；不注入故障。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. `GET /healthz`、`GET /readyz` —— 确认 §2.1 基线（由 `pytest_configure` 自动执行，本 case 不重复）。
  2. `resp = admin_client.get("/v1/service-levels/Worker")`；记录 status、headers、body。
  3. 断言 `resp.status_code == 200`。
  4. 解析 body：断言键集**恰为** `{id,deployment_ids,enabled,capabilities,version}`（`additionalProperties:false`）；`id=="Worker"`、`deployment_ids` 为数组、`enabled` 为 bool、`version` 为 int ≥1、`capabilities` 为 12 键 `ModelCapabilities`。
  5. 断言响应头含 `ETag`，且匹配强 ETag 形态 `^"[A-Za-z0-9._:-]+"$`（期望 `"Worker.v<N>"`，`N==body.version`）。

**重点关注步骤**：① **精确 id 匹配**——`Worker` 区分大小写；`worker`/`WORKER` 应 404（未在本 case 构造，但不得把大小写不匹配当 PASS）；② **字段集精确**——`ServiceLevelView.additionalProperties:false`，多/少键即 FAIL；③ **ETag identity**——ETag 必为 `"<id>.v<version>"` 且与 body `version` 一致（含双引号），是把详情读与后续 CAS 绑定的关键；④ **capabilities 12 键**——必须为完整 `ModelCapabilities`，不是子集；⑤ **读无副作用**——`GET` 不写 `query_snapshots`（非分页 `page`）、不改 version。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ServiceLevelView` + ETag 规则。
  - HTTP：`200`；响应头 `ETag == "Worker.v<N>"`（`N` 与 body `version` 同）。
  - body：`{"id":"Worker","deployment_ids":[...],"enabled":<bool>,"capabilities":{…12…},"version":N}`。
  - 无错误信封。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：`200` + `ServiceLevelView` 键集/类型正确 + `id=="Worker"` + `ETag=="Worker.v<N>"` 且与 `version` 一致。
  - **FAIL**：status 非 200、键集不符、`id` 错、ETag 缺失/格式错/与 version 不一致。
  - **BLOCKED**：fixture/断言逻辑问题——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：§2.1 前置不满足——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：用 `127.0.0.1`/mock 冒充真实 m5air——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（§3.2 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**无需 teardown**——只读 `GET`，不改 `service_levels`/`service_level_deployments`、不写注入。退出前确认 `/readyz` 仍 7 tier、`GET /v1/service-levels/Worker` 的 `version` 未变。 若被误跑于 B 类实例则整班 `stop()` + `rm -rf`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。

## 7. 自动化位置与状态

- **证据与 Run**：保存原始 HTTP status/headers（含 `ETag`）/body、发出命令、exit code、`elapsed`、环境快照；落位与契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)（Run ID=`<date>/A-api`，`environment:"a"`，`manifest.json` 含 `target_artifact`/`redactions`/`reproduction_cmd`）。

- **依赖**：[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) 就绪检查；`admin_client` fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)(../llmtier-system-test-scheme.md)）；`ServiceLevelView` 机器契约；`registry.get_service_level`/`_etag`。自动化入口 [`ST-SL-003.py`](../../../../tests/system/cases/ST-SL-003.py)。**不依赖**其它 Case；其 ETag 语义被 ST-SL-004/04b/05 复用但各自独立执行。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
