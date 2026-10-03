<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-PROV-013 — usage 子对象更新

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-PROV-013` |
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
| Template Conformance | `native` |
| Tailoring Reference | none |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/system/cases/ST-PROV-013.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-PROV-013`）；责任摘要、分类与优先级以 [系统测试方案 §6](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 Provider CRUD 接口（/v1/providers）（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-002`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-PROV-013` 可追到方案清单行与 Run 报告。

> 本 Case 文档绑定：系统设计经 `--parent-document-id`、所属方案经方案清单行引用写入 metadata；Document ID＝Case ID。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-PROV-013` / 系统设计 §8 Provider CRUD 接口（/v1/providers） / `VRC-MGMT-002` / `normal` / `P2`
- **测试方法（§2.2 方法表行）**：等价类划分 + 契约字段比对
- 方案清单登记：`ST-PROV-013`（与 计划 §3 权威清单一致；本文件名 `st-prov-013.md`，唯一对应）。
- 要测什么（责任展开）：`PATCH /v1/providers/{id}` 更新 `usage` 子对象（`max_concurrent_requests`）：HTTP 200，且回读可见新值，随后复位。
- 明确不测什么 / 失败含义：不证明 标量字段更新（ST-PROV-005）、不证明 `usage` 校验负向（非法 `usage_provider`/`*_ref`/负值 → 400，见 `_usage_values`，未单列 case）、不证明 `/v1/providers/{id}/usage` 快照刷新（ST-PUSAGE-*）；本 case 只验证合法 `usage` 子对象的持久化与复位。

**目的（被测契约）**：验证 Management Provider CRUD 的**嵌套配置更新契约**。被测端点/规则：`PATCH /v1/providers/{id}`（[openapi](../../../../interfaces/openapi/llmtier.openapi.json) `updateProvider`，`ProviderPatch.usage → ProviderUsageProfileWrite`）；
[`registry.update_provider`](../../../../src/management/registry.py) 对 `usage` 走 `_usage_values(body.get("usage"), values["kind"], current)` 合并/校验并写 `provider_usage_profiles`（`version` 推进），且**清空该 provider 的 usage 快照**（`DELETE FROM provider_usage_snapshots`）；
`If-Match` 必须匹配当前 ETag；成功 `200` + 新 `ProviderView`（`usage.max_concurrent_requests` 为新值）。设计验证项 `VRC-MGMT-002`；机制 `T-CFG-CAS`；
需求/机制链 `LT-FUN-005`、`R-CFG-01`、`CT-ADMIN-001`。**不证明什么**：不证明标量字段更新（ST-PROV-005）、不证明 `usage` 校验负向（非法 `usage_provider`/`*_ref`/负值 → 400，见 `_usage_values`，未单列 case）、不证明 `/v1/providers/{id}/usage` 快照刷新（ST-PUSAGE-*）；
本 case 只验证合法 `usage` 子对象的持久化与复位。

## 2. 被测入口与前置

- **前置与环境**：**环境 B**（临时 LLMTier 实例 + 临时 SQLite；见[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。执行前须满足[系统测试计划 §3 执行前检](../llmtier-system-test-plan.md#3-执行前检go--no-go) **附加（B 类）**：实例 `/healthz` 200；`_baseline_settings` 注入 1 provider（`prov_b`）+ 1 deployment（`depl_b`）+ 7 fixed tier。fixture（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）：`llmtier_b`、`admin_client_b`。初始状态：m5air 上级基线由 `_baseline_settings` 提供；`depl_b` probe `healthy`。本 case 直接更新 baseline `prov_b` 的 usage（**必须复位**，见清理）。

## 3. 输入构造

- **输入与构造**：固定两步（先取真实 ETag，再 PATCH）：
  ```http
  GET /v1/providers/prov_b HTTP/1.1
  Authorization: Bearer dev-admin

  PATCH /v1/providers/prov_b HTTP/1.1
  Authorization: Bearer dev-admin
  If-Match: "<GET 返回的 ETag>"
  Content-Type: application/json
  ```
  ```json
  {"usage": {"max_concurrent_requests": 5}}
  ```
  构造点：`If-Match` **取自 `GET` 响应头**（绝不硬编码；B 类前序写 case 会推进 `prov_b` 版本）；`usage.max_concurrent_requests=5`（≥1 的合法整数，区别于默认值 1，便于观测生效）；PATCH 体仅含 `usage`（`minProperties:1` 满足）。不注入故障；不构造非法输入（非法 usage 字段负向不在本 case）。

## 4. 执行步骤与观察点

- **执行过程（逐步调用）**：
  1. （fixture 前置）`llmtier_b` `/healthz` 200；`_probe_deployment(depl_b)` 断言 `healthy`。
  2. `current = admin_client_b.get("/v1/providers/prov_b")`；断言 `200`，记 `original = current.json()["usage"]["max_concurrent_requests"]`、`original_version = current.json()["version"]`、`etag = current.headers["ETag"]`。
  3. `patch = admin_client_b.patch("/v1/providers/prov_b", json={"usage":{"max_concurrent_requests":5}}, headers={"If-Match": etag})`；断言 `200`。
  4. 解析 `patch.json()`：`usage.max_concurrent_requests == 5`；`patch.json()["version"] > original_version`；响应头含新 `ETag`。
  5. `after = admin_client_b.get("/v1/providers/prov_b")`；断言 `200`、`usage.max_concurrent_requests == 5`（持久化）。
  6. （teardown，`finally` 强制）`restore = GET`；若 `restore.usage.max_concurrent_requests != original`，以 `restore` 的 ETag `PATCH` 回 `{"usage":{"max_concurrent_requests": original}}`；再 `GET` 断言已复位。

**重点关注步骤**：① **嵌套更新语义**——`usage` 子对象按白名单键合并，只改提交字段，其余保留；② **`If-Match` 实取**——B 类共享 session，`prov_b` 版本受前序 case 影响，硬编码必 412；
③ **持久化回读**——第 5 步确认 5 生效而非仅响应回显；④ **容量约束**——`max_concurrent_requests` 必须 ≥1（`_usage_values` 校验），本 case 用 5；⑤ **快照副作用**——更新 `usage` 会删除该 provider 的 usage 快照（`provider_usage_snapshots`），这是既定行为，报告须登记；
⑥ **复位必达**——`prov_b` 是全 B 类 session 的 baseline，必须恢复原值（版本会前进，但值复原），否则影响后继 case（如 ST-PROV-010 取 ETag 仍能工作，但值被污染）。

## 5. 独立 Oracle 与预期结果

> 判据语义以设计验证项（VRC）为唯一权威，本文细化为可执行断言但不改写；冲突回溯设计修订。

- **期望结果与独立 Oracle**：独立 Oracle = `openapi` `ProviderPatch.usage`/`ProviderUsageProfileView` + `_usage_values` 规则。
  - GET：`200`，`usage.max_concurrent_requests == original`（默认 1）。
  - PATCH：`200`；body `usage.max_concurrent_requests == 5`；`version` 推进；新 `ETag`。
  - 回读：`200` 且值 5。
  - teardown：恢复 `original` 并回读确认。

- **判定（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
  - **PASS**：PATCH `200` 且 `usage.max_concurrent_requests==5`、`version` 推进；回读一致；teardown 复位成功。
  - **FAIL**：任意步骤 status/字段不符、值未持久化、或 teardown 未复位（污染 baseline）。
  - **BLOCKED**：无法执行/无法判定且可重试（fixture/断言逻辑问题）——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **SKIP**：B 类临时实例/fixture 不可用——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **INVALID**：硬编码/伪造 ETag 绕过 CAS、或用 mock 冒充——见[系统测试计划 §7 报告产出与 Gate 规则](../llmtier-system-test-plan.md#7-报告产出与-gate-规则)。
  - **NOT_RUN**：本 Case 有实现（计划 §3 实现盘点 `RUN`），本轮未执行时按 §9 记 `NOT_RUN`。

## 6. 错误路径、副作用与清理

- **清理与复位**：**必须 teardown（`finally` 强制）**——把 `prov_b.usage.max_concurrent_requests` 恢复为初始 `original`（先 `GET` 取新 ETag 再 PATCH）；不改 `prov_b` 其它字段/`depl_b`、不写注入。B 类整班结束由 fixture `stop()` + `rm -rf` 销毁（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）。离开前 `GET` 确认已复位、`/readyz` 7 tier。

## 7. 自动化位置与状态

- **证据与 Run**：证据与 Run 契约见[系统测试计划 §6 证据与 Run 记录规则](../llmtier-system-test-plan.md#6-证据与-run-记录规则)：Run ID=`<date>/B-api`；保存请求与原始响应（脱敏后）、发出命令、exit code、`elapsed`、环境快照；`manifest.json` 必填字段与报告落位（`tests/system/reports/...`）见计划 §7/§10；失败现场不截断。**本 case 额外证据**：初始 GET、PATCH 请求/响应（含 `If-Match`/`ETag`）、回读、复位 PATCH/回读。

- **依赖**：B 类 fixture `llmtier_b` / `admin_client_b` 与 baseline `prov_b`（[系统测试计划 §5 环境操作](../llmtier-system-test-plan.md#5-环境操作搭建--复位--隔离--清理)）；`ProviderPatch`/`ProviderUsageProfileWrite`/`ProviderUsageProfileView` 机器契约；`registry.update_provider`/`_usage_values`；机制 `T-CFG-CAS`；自动化入口 [`ST-PROV-013.py`](../../../../tests/system/cases/ST-PROV-013.py)。**不依赖**其它 Case（自复位）；与 ST-PROV-005 同属 PATCH 但本 case 专测嵌套 `usage`。

> 实现状态：见上文「证据与 Run」与「依赖」中的自动化入口（Planned/Implemented）；执行状态与 Verdict 只在 Run 报告。
