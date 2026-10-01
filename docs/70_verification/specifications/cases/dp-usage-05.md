<!-- STD_DOCUMENT_COVER_BEGIN -->
# DP-USAGE-05 — 缺 `from`/`to`

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `DP-USAGE-05` |
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
| Canonical Path | `docs/70_verification/specifications/cases/dp-usage-05.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`DP-USAGE-05`）；责任摘要、分类与优先级以 [系统测试方案 §3](../../schemes/llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 Usage 查询接口（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-006`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `DP-USAGE-05` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`DP-USAGE-05` / 系统设计 §8 Usage 查询接口 / `VRC-MGMT-006` / negative / P1（[方案清单 `DP-USAGE-05`](../../schemes/llmtier-system-test-scheme.md)）。
- **测试方法（§1.5 方法表行）**：错误猜测 + 反例驱动（ERR-*）
- 要测什么（责任展开）：`GET /v1/usage` 缺 `from` 或 `to`（或二者）→ `400 invalid_request`；非法 `date-time` 或 `from >= to` 同样 400，且在**建 snapshot / 读账本之前**被拒（零副作用）。`from`/`to` **required** `date-time`。实现：handler `src/http_api/app.py` 在 `not since or not until` 时直接 `ApiError(400,"invalid_request","from and to are required")`（在建快照前）；`src/inference/usage.py::_page` 在做 `from`/`to` 解析失败或 `start >= end` 时 `ApiError(400,"invalid_request",...)`（仍在 `query_snapshots` 写入前）。机制需求 `R-MET-04`（HTTP 适配层错误映射）；错误目录 `ERR-REQ-VALIDATION` → `invalid_request`；需求链 `LT-FUN-004`、`LT-INT-004/005/007`、`CT-USAGE-001`。
- 明确不测什么 / 失败含义：不测正常查询（DP-USAGE-01/03）；不测过期 cursor 的 `cursor_expired`（DP-USAGE-04）；不测 filter/cursor 不匹配的 `invalid_request`（属 DP-USAGE-07 的 cursor 组件）；不测主体隔离（DP-USAGE-06）；不测 store 不可用 → 503（DP-USAGE-08）；也不测 `limit` 范围校验（实现只做整数转换）。失败含义＝Usage 查询请求校验契约破坏。

## 2. 被测入口与前置

- 被测入口声明与位置：Data Plane `GET /v1/usage`；角色 `data`，只读/无状态。

```text
GET /v1/usage
GET /v1/usage?from=<now-30d>
GET /v1/usage?to=<now>
GET /v1/usage?from=&to=
GET /v1/usage?from=not-a-date&to=<now>
GET /v1/usage?from=<now-30d>&to=2026-13-45
GET /v1/usage?from=<now>&to=<now-30d>
GET /v1/usage?from=<now>&to=<now>
Authorization: Bearer dev-data
```

- 初态构造（经公开入口）：**环境 A**（m5air 已部署实例，只读/无状态）。初始状态 = m5air 现有基线。
- Fixture / 向量及版本：7 个非法/缺失变体 + 1 次合法对照；动态值（`constants.recent_window()` 或 `now()`），禁止硬编码日期。
- 依赖的测试资产（tests.asset-design 文档）：`api_client`；可选 `ssh m5air sqlite3`（仅加强证据）。

## 3. 输入构造

- 逐参数输入构造：对 `GET /v1/usage` 逐项构造非法/缺失查询（同一 `api_client`，不注入故障）：
  1. 无任何查询参数：`GET /v1/usage`
  2. 仅 `from`：`GET /v1/usage?from=<now-30d>`
  3. 仅 `to`：`GET /v1/usage?to=<now>`
  4. 空串：`GET /v1/usage?from=&to=`
  5. 非法日期：`GET /v1/usage?from=not-a-date&to=<now>`
  6. 非法日期：`GET /v1/usage?from=<now-30d>&to=2026-13-45`
   7. 逆序 `GET /v1/usage?from=<now>&to=<now-30d>` 与**等值** `from=<now>&to=<now>`（`start >= end` 两个边界）
- 边界/非法取值及理由：`from`/`to` 用动态值（`constants.recent_window()` 或 `now()`），**禁止硬编码日期**；合法值仅用于构造对照（变体 5/7）。
- 规模 / 时间域：7 个变体 + 1 次对照；全部在建快照前被拒。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `GET /healthz`/`GET /readyz`（`pytest_configure` 完成，不重复） | §2.1 基线 |
| 2 | 逐个变体发 `GET /v1/usage` | `status_code == 400` |
| 3 | 对每个响应断言 `err = body["error"]` | `err["code"] == "invalid_request"`、`err["type"] == "request_error"`、信封键集恰 `{message,type,code,param,retryable}`；`param` 为 `null`（实现未设 param，不强制其它值） |
| 4 | （零副作用交叉核对，可选）若具备 `ssh m5air sqlite3`，在变体前后 `SELECT COUNT(*) FROM query_snapshots;` | 计数**不变**（校验"校验先于建 snapshot"）；无 SSH 权限时跳过该子检查，**不**因此判变体失败 |
| 5 | （对照，不改变本 case 判定）对同一 `api_client` 发一次**合法**查询 `?from&to` | 返回 200——佐证拒绝来自参数而非端点/存储不可用 |

- 重点关注步骤：① **缺参 vs 坏日期都要 400 `invalid_request`**——`not since or not until` 在 handler 层、日期解析/`from>=to` 在 `_page` 层，两处都要覆盖；② **空串视同缺失**——`query.get("from",[None])[0]` 得到 `""` 为假值，应走 `invalid_request`；③ **零副作用**——拒绝必须发生在 `query_snapshots` INSERT 之前；④ **错误信封 identity**——恰 5 键、无 `category`，`type` 由 `<500` 导出为 `request_error`；⑤ **不夸大**——`param` 实现为 `null`，不断言具体字段名；⑥ **等值边界**——`from==to` 与逆序 `from>to` 均须 400 `invalid_request`（同一 `start >= end` 分支）。

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：OpenAPI `from`/`to` `required:true` + `ERR-REQ-VALIDATION` 目录（不依赖实现消息文本）。**判据语义以设计验证项 `VRC-MGMT-006` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：变体 1–7：HTTP `400`；`error.code=="invalid_request"`；`error.type=="request_error"`；信封恰 5 键；对照合法查询：`200`；可选：`query_snapshots` 计数不变。

## 6. 错误路径、副作用与清理

- 错误出口与表现：任一变体返回非 400，或 `code`/`type` 不符，或返回错误信封以外形态（如 200 空页）。
- 副作用断言与清理：**无需 teardown**——全部请求在 dispatch/建快照前被拒，不产生状态变更；不创建/修改 provider/deployment/service-level、不写注入、不删除用户 usage。退出前 `/readyz` 仍 7 tier；若误跑 B 类则按计划销毁。

## 7. 自动化位置与状态

- 测试文件 / 测试函数：`tests/system/api_test_v03/at_dp_usage_05.py`（已实现；7 个非法变体含 `from==to` 等值边界 + 1 次合法对照）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/at_dp_usage_05.py -q`。
- 实现状态：Implemented；执行与 Verdict 归 Run 报告。

**判定口径（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
- PASS：变体 1–7 均 `400 + invalid_request + request_error`，合法对照 `200`（可选的计数不变不改变结论）。
- FAIL：任一变体返回非 400，或 `code`/`type` 不符，或返回错误信封以外形态（如 200 空页）。
- BLOCKED：断言逻辑/契约问题（如 `param` 语义不清）。
- SKIP：就绪检查不满足。
- INVALID：用 mock/替代路径冒充真实路径。
- NOT_RUN：本 Case 有实现，本轮未执行时记 `NOT_RUN`。

**证据与 Run**：Run ID=`<date>/A-api`；保存 7 个变体的完整请求（含 query 实际值）与原始 status/headers/body、对照合法查询响应、可选 `ssh sqlite3` 的 `COUNT(*)` 前后值、发出命令、exit code、`elapsed`、环境快照（本 case `environment:"a"`）。

**依赖**：就绪检查；`api_client`；`constants.recent_window()` 动态值；`listUsage` 机器契约与 `ERR-REQ-VALIDATION`；可选 `ssh m5air sqlite3`（仅加强证据，非 PASS 必要条件）。自动化入口 `at_dp_usage_05.py`（已实现）。**不依赖**其它 Case；与 DP-USAGE-01（正常查询）、DP-USAGE-04（过期 cursor）区分参数缺失/坏值与 cursor 过期两类 400。
