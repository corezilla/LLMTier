<!-- STD_DOCUMENT_COVER_BEGIN -->
# DP-USAGE-01 — Usage 时间窗查询

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `DP-USAGE-01` |
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
| Canonical Path | `docs/70_verification/specifications/cases/dp-usage-01.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`DP-USAGE-01`）；责任摘要、分类与优先级以 [系统测试方案 §3](../../schemes/llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 Usage 查询接口（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-006`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `DP-USAGE-01` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`DP-USAGE-01` / 系统设计 §8 Usage 查询接口 / `VRC-MGMT-006` / normal / P0（[方案清单 `DP-USAGE-01`](../../schemes/llmtier-system-test-scheme.md)）；机制 `T-MET-PAGE`、`T-MET-FINAL`（[usage-metering 机制](../../../20_system_design/mechanisms/usage-metering.md) §4.5/§4.7 CON-METER-004）。
- **测试方法（§1.5 方法表行）**：等价类划分 + 契约字段比对
- 要测什么（责任展开）：`GET /v1/usage` 以**动态时间窗**查询返回合法 `UsagePage`：`from`/`to` 必填且 `from<to`，`data[]` 全部落在 `[from,to)`，`next_cursor`/`has_more` 同步、含 `snapshot_id`/`snapshot_at`。`from`/`to` **必填** `date-time`，服务端按 `[from,to)`（`from` 含、`to` 不含）与稳定排序 `(recorded_at,request_id)` 返回 `UsagePage`（`data[]` + `next_cursor` + `has_more` + `snapshot_id` + `snapshot_at`，`additionalProperties:false`）；首屏在单事务内创建 `query_snapshots` 并冻结有序成员（实现 `src/inference/usage.py::UsageRecorder._page`）。机制需求 `R-MET-02`；需求链 `LT-FUN-004`、`LT-INT-004/005/007`、`CT-USAGE-001`/`CT-STORE-001`；错误码 `invalid_request`、`permission_denied`、`usage_store_unavailable`。
- 明确不测什么 / 失败含义：不测某次调用后的记录内容/账本终态（DP-USAGE-02）；不测 `limit=1` 分页推进（DP-USAGE-03）；不测过期 cursor 拒绝（DP-USAGE-04）；不测主体隔离（DP-USAGE-06）；不测 cursor 重放幂等（DP-USAGE-07）；不测 store 不可用 → 503（DP-USAGE-08）；不测 `DELETE /v1/usage`（ADM-USAGE-03）。失败含义＝UsagePage wire 契约或时间窗语义破坏。

## 2. 被测入口与前置

- 被测入口声明与位置：Data Plane `GET /v1/usage`；角色 `data`，只读/无状态。

```text
GET /v1/usage?from=<now-30d>&to=<now>
Authorization: Bearer dev-data
Accept: application/json
```

- 初态构造（经公开入口）：**环境 A**（m5air 已部署实例，只读/无状态）。初始状态 = m5air 现有 3 provider / 4 deployment / 7 fixed tier。**时间窗必须动态**：由 `constants.recent_window()` 以 `now()` 生成最近窗口（默认 30×24 h），**禁止硬编码日期**，避免历史数据随日期迁移而失效。
- Fixture / 向量及版本：动态窗口（`recent_window()`）；不传 `cursor`（首屏）、不传 `limit`（默认 100）、不传 `model`/`request_id`（窗口全量）。
- 依赖的测试资产（tests.asset-design 文档）：`api_client`（data 主体 `principal_id=consumer`）；`constants.recent_window()`；`conftest.py::pytest_configure` 就绪检查。

## 3. 输入构造

- 逐参数输入构造：固定请求（动态窗口，无 body）：`GET /v1/usage?from=<now-30d>&to=<now>`，`Authorization: Bearer dev-data`。
- 边界/非法取值及理由：`from`/`to` 为 RFC3339 UTC（秒精度，`Z` 后缀），`from<to`；不传 `cursor`（首屏）、不传 `limit`（用默认 100）、不传 `model`/`request_id`（窗口全量）。不注入故障；不构造非法输入（缺参/坏日期归 DP-USAGE-05）。
- 规模 / 时间域：单次查询；默认 `limit=100`；不发布时延 SLO。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `GET /healthz`、`GET /readyz`（`pytest_configure` 自动执行） | §2.1 基线 |
| 2 | `since, until = recent_window()`；`resp = api_client.get("/v1/usage", params={"from": since, "to": until})` | status/headers |
| 3 | 断言 status 与形态 | `status_code == 200` 且 content-type 含 `application/json`（非错误信封） |
| 4 | 解析 body，键集**恰为** `{data,next_cursor,has_more,snapshot_id,snapshot_at}`（`additionalProperties:false`） | 键集精确 |
| 5 | 断言 `data` 为数组；`has_more` 为 JSON 布尔；`next_cursor` 为 `null` 或非空字符串，且**当且仅当** `has_more=false` 时为 `null`；`snapshot_id` 非空字符串；`snapshot_at` 为 RFC3339 `date-time` | openapi `if/then` 不变式 |
| 6 | 对 `data` 每条记录断言 `UsageRecord` 必填键齐备 | `endpoint ∈ {"/v1/responses","/v1/embeddings"}`；`measurement_status ∈ {measured,estimated,unknown}`；`source ∈ {provider,gateway_estimate,unavailable}`；`unknown ⇒ 各 token 字段为 null`（INV-5） |
| 7 | 对每条记录断言 `recorded_at >= since` 且 `recorded_at < until` | `[from,to)` 边界 |

- 重点关注步骤：① **时间窗动态化**——`from`/`to` 必须由执行时刻生成，不得写死；② **`next_cursor`/`has_more` 同步**——"`has_more=false ⇒ next_cursor=null`"这一 openapi 不变式；③ **键集精确**——`UsagePage` `additionalProperties:false`，多键/缺键即 FAIL；④ **`[from,to)` 半开区间**——`recorded_at == to` 的记录必须被排除，`== from` 必须包含；⑤ **不把错误当空页**——非 200 时必须确认是可解释的 `ERR-AUTH-*`/`ERR-STORE` 信封；⑥ **不夸大**——本 case **不**断言 `data` 非空，空 `data` + 合法 `snapshot_id`/`snapshot_at` 仍是 PASS。注意：现有 [`at_dp_usage_01.py`](../../../../tests/system/api_test_v03/at_dp_usage_01.py) 已覆盖步骤 3/5，但**未**断言步骤 4 的精确键集与步骤 6/7；覆盖缺口须补齐后方可判 PASS。

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：OpenAPI `UsagePage`/`UsageRecord` 的 wire 形态 + 机制 `[from,to)`/稳定排序语义（不依赖实现的输出内容）。**判据语义以设计验证项 `VRC-MGMT-006` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：HTTP `200`；`Content-Type: application/json`；body 键集恰为 `{data,next_cursor,has_more,snapshot_id,snapshot_at}`；`data` 为数组，元素满足 `UsageRecord`；`has_more=false ⇒ next_cursor is null`；`snapshot_id` 非空；`snapshot_at` 合法 RFC3339；每条 `data[].recorded_at ∈ [from,to)`；`measurement_status=unknown` 时 token 字段为 `null`（非 `0`）。

## 6. 错误路径、副作用与清理

- 错误出口与表现：存储健康时非 200、键集不符、`has_more`/`next_cursor` 不变式破裂、记录字段/枚举错、`recorded_at` 越界、unknown 却填 0，均为 FAIL。
- 副作用断言与清理：**无需 teardown**——纯读 `GET`，不改 provider/deployment/service-level、不写注入项、不删除用户 usage；唯一副作用是服务端创建一条 10 分钟 TTL 的 `query_snapshots` 首屏快照（只读查询的正常产物，非需复位状态）。退出前确认 `/readyz` 仍 7 tier 且无未清空注入项；若误跑于 B 类实例，按计划整班销毁。

## 7. 自动化位置与状态

- 测试文件 / 测试函数：[`tests/system/api_test_v03/at_dp_usage_01.py`](../../../../tests/system/api_test_v03/at_dp_usage_01.py)（脚本须补齐步骤 4/6/7）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/at_dp_usage_01.py -q`。
- 实现状态：Implemented；执行与 Verdict 归 Run 报告。

**判定口径（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
- PASS：`status==200` 且 body 键集/类型/不变式、`UsageRecord` 必填项、`[from,to)` 区间与 unknown⇒null 全部 match。
- FAIL：status 非 200（存储健康时）、键集不符、`has_more`/`next_cursor` 不变式破裂、记录字段/枚举错、`recorded_at` 越界、unknown 却填 0。
- BLOCKED：测试代码/契约本身问题（断言不可实现、解析器错）。
- SKIP：就绪检查不满足（m5air 不可达、`/readyz` 非 7 tier、双 OMLX 离线等）。
- INVALID：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径。
- NOT_RUN：本 Case 有实现，本轮未执行时记 `NOT_RUN`，不得以未跑冒充 PASS。

**证据与 Run**：Run ID=`<date>/A-api`；保存原始 status/headers/body（脱敏后）、发出命令、exit code、`elapsed`、环境快照（本 case `environment:"a"`）。

**依赖**：就绪检查；`api_client`；`constants.recent_window()` 动态窗口；`UsagePage`/`UsageRecord` 机器契约；机制 [`usage-metering` §4.5/§4.7](../../../20_system_design/mechanisms/usage-metering.md)；自动化入口 `at_dp_usage_01.py`。**不依赖**其它 Case；与 DP-USAGE-02/03（记录可见/分页）、DP-USAGE-05（缺参负向）语义相邻但各自独立执行。
