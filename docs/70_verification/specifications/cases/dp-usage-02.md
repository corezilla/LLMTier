<!-- STD_DOCUMENT_COVER_BEGIN -->
# DP-USAGE-02 — 请求后可见记录

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `DP-USAGE-02` |
| Document Version | `0.1.0-draft.2` |
| Status | `Draft` |
| Project | `LLMTier` |
| Authority | `LLMTier` |
| Document Owner | LLMTier |
| Authors | LLMTier |
| Created Date | `2026-09-29` |
| Last Modified Date | `2026-09-30` |
| Template ID | `tests.system-case` |
| Template Version | `2.3.2` |
| Template Conformance | `tailored` |
| Tailoring Reference | std-tailoring |
| Migration Map Reference | none |
| Repository | `corezilla/LLMTier` |
| Canonical Path | `docs/70_verification/specifications/cases/dp-usage-02.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`DP-USAGE-02`）；责任摘要、分类与优先级以 [系统测试方案 §3](../../schemes/llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 Usage 查询接口（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-006`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `DP-USAGE-02` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`DP-USAGE-02` / 系统设计 §8 Usage 查询接口 / `VRC-MGMT-006` / normal / P1（[方案清单 `DP-USAGE-02`](../../schemes/llmtier-system-test-scheme.md)）；机制 `T-MET-FINAL`（[usage-metering 机制](../../../20_system_design/mechanisms/usage-metering.md) §4.5/§4.6 CON-METER-001..003，INV-1/2/3）。
- 要测什么（责任展开）：一次成功的 `POST /v1/embeddings` 之后，其 `request_id` 在同一动态窗口的 `GET /v1/usage` 中可见，记录为 head 终态（`is_final=true`）、`endpoint`/`model` 与调用一致。前置 `POST /v1/embeddings`（生成一条账本义务并 `finish` 为终态版本），随后 `GET /v1/usage`（支持 `request_id` 过滤）读取。实现为 `src/inference/usage.py`：dispatch 前 `authorize_dispatch` 写 `usage_obligations` v1（`unknown`），成功 `finish` 追加 v2（`measured`，head 单调推进，读取只取 head 单条、不累加）。机制需求 `R-MET-01`/`R-MET-02`；需求链 `LT-FUN-004`、`LT-INT-004/005/007`、`CT-USAGE-001`。
- 明确不测什么 / 失败含义：不测 token 计量数值的准确性（上游未回 usage 时按 `unknown`+`null` 收敛，属正常）；不测分页（DP-USAGE-03）、过期 cursor（04）、主体隔离（06）、重放幂等（07）、store 不可用（08）；不测答案/向量内容正确性。失败含义＝终态账本可见性契约破坏。

## 2. 被测入口与前置

- 被测入口声明与位置：Data Plane `POST /v1/embeddings`（前置写）与 `GET /v1/usage`（读取）；角色 `data`，一次性无状态写后立即回收。

```text
POST /v1/embeddings
GET  /v1/usage?from=<now-30d>&to=<now>&request_id=<rid>
Authorization: Bearer dev-data
```

- 初态构造（经公开入口）：**环境 A**（m5air 已部署实例，一次性无状态写后立即回收）。m5air 存在可路由的 embeddings-capable deployment（`dep_local_bge_m3`，固定 tier `Embedding-v1`）。**关键前置**：若该 deployment 不 healthy，`/readyz` 会暴露，按就绪检查处理。窗口由 `constants.recent_window()` 动态生成（**禁止硬编码日期**）。
- Fixture / 向量及版本：前置调用固定 prompt/输入（`input=["llmtier-usage-02-probe"]`），随 Run manifest 存档。
- 依赖的测试资产（tests.asset-design 文档）：`api_client`（data 主体 `principal_id=consumer`）；`constants.recent_window()`；`conftest.py::pytest_configure` 就绪检查。

## 3. 输入构造

- 逐参数输入构造：先发前置调用（固定 prompt/输入），再查询：

```json
{"model": "Embedding-v1", "input": ["llmtier-usage-02-probe"], "encoding_format": "float"}
```

随后 `GET /v1/usage?from=<now-30d>&to=<now>&request_id=<rid>`。

- 边界/非法取值及理由：`model="Embedding-v1"` 指 embeddings tier；输入为固定短字符串（确定性、无随机）；`request_id` 取前置响应的 `X-Request-ID` 头（服务端为**本次**请求生成的 `req_<hex>`），用 `request_id` 过滤把窗口噪声排除，使断言确定；窗口 `[from,to)` 覆盖调用时刻。
- 规模 / 时间域：1 次写 + 1 次查询；按 `request_id` 过滤使结果确定。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `GET /healthz`、`GET /readyz`（`pytest_configure` 完成，本 case 不重复） | §2.1 基线 |
| 2 | `emb = api_client.post("/v1/embeddings", json={...})` | `emb.status_code == 200`；`rid = emb.headers["X-Request-ID"]` 非空（服务端恒发该头） |
| 3 | `since, until = recent_window()`；`resp = api_client.get("/v1/usage", params={"from": since, "to": until, "request_id": rid})` | `200` |
| 4 | `body = resp.json()` | `len(body["data"]) == 1` 且 `body["data"][0]["request_id"] == rid` |
| 5 | 断言该记录 `endpoint=="/v1/embeddings"`、`model=="Embedding-v1"`、`is_final is True`、`record_version >= 1` | head 终态；不是 v1 obligation |
| 6 | 断言 `measurement_status ∈ {measured,estimated,unknown}` 且 `source` 与之一致 | `measured⇒provider`、`estimated⇒gateway_estimate`、`unknown⇒unavailable`；`unknown` 时 token 字段全为 `null`（**不得为 0**，INV-5）；否则为非负整数 |
| 7 | 断言 `recorded_at`/`updated_at` 为合法 RFC3339 且 `recorded_at ∈ [since,until)` | `[from,to)` 边界 |

- 重点关注步骤：① **`request_id` 捕获**——必须取前置响应头 `X-Request-ID`（服务端生成），不要自行编造；② **head 单条、不累加**——`data` 中同一 `request_id` 只应出现一条（head 指向的版本），若出现同 `request_id` 的多条即 FAIL；③ **终态而非 v1 obligation**——`is_final=true` 且 `record_version>=1`；④ **unknown ⇒ NULL 而非 0**——`T-MET-UNKNOWN`/INV-5 的强断言；⑤ **不夸大计量**——不对 token 数值做业务断言；⑥ **窗口动态**。注意：现有 [`at_dp_usage_02.py`](../../../../tests/system/api_test_v03/at_dp_usage_02.py) **未自建前置调用、未按 `request_id` 过滤、未断言 `is_final`/head 唯一/unknown⇒null**；脚本须补齐后方可判 PASS。

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：机制 `T-MET-FINAL`（`authorize_dispatch` → `finish` 后 head 指向单一终态版本，`GET /v1/usage` 只暴露该 head）+ OpenAPI `UsageRecord`。**判据语义以设计验证项 `VRC-MGMT-006` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：前置 `POST /v1/embeddings`：`200`，响应头 `X-Request-ID=rid`；`GET /v1/usage?request_id=rid`：`200`，`data` 恰 1 条，`request_id==rid`、`model=="Embedding-v1"`、`endpoint=="/v1/embeddings"`、`is_final=true`、`record_version>=1`；`unknown ⇒ tokens all null`；`recorded_at ∈ [from,to)`。

## 6. 错误路径、副作用与清理

- 错误出口与表现：查询 `200` 但 `data` 不含该 `request_id`、或含多条、或 `is_final` 非真、或 `endpoint`/`model` 不符、或 `unknown` 却填 0、或 `recorded_at` 越界。
- 副作用断言与清理：**A 类一次性无状态写**——前置 embeddings 调用会向账本写一条 usage fact；这是被测行为本身，**不删除用户 usage**（明确不得删除 m5air 既有/用户 usage），故**无 teardown**。仅确认不误建 provider/deployment/service-level、不写注入项；退出前 `/readyz` 仍 7 tier。若被误跑于 B 类临时实例，则按计划整班销毁。

## 7. 自动化位置与状态

- 测试文件 / 测试函数：[`tests/system/api_test_v03/at_dp_usage_02.py`](../../../../tests/system/api_test_v03/at_dp_usage_02.py)（脚本须补齐前置调用与上述断言）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/system/api_test_v03/at_dp_usage_02.py -q`。
- 实现状态：Implemented；执行与 Verdict 归 Run 报告。

**判定口径（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
- PASS：前置调用 `200` 且查询 `200`，且 `data` 恰 1 条满足 `request_id`/`model`/`endpoint`/`is_final`/`record_version`/`measurement_status-source-token` 一致与 `[from,to)`。
- FAIL：查询 `200` 但 `data` 不含该 `request_id`、或含多条、或 `is_final` 非真、或 `endpoint`/`model` 不符、或 `unknown` 却填 0、或 `recorded_at` 越界。
- BLOCKED：测试代码/契约本身问题，或 embeddings 前置无法命中。
- SKIP：就绪检查不满足（embeddings deployment 不可用、上游离线等）。
- INVALID：用 `127.0.0.1`/mock/替代路径冒充真实 m5air 路径。
- NOT_RUN：本 Case 有实现，本轮未执行时记 `NOT_RUN`。

**证据与 Run**：Run ID=`<date>/A-api`；保存前置 `POST /v1/embeddings` 的请求/响应（含 `X-Request-ID`）、随后的 `GET /v1/usage?request_id=...` 请求/响应、动态窗口实际值、发出命令、exit code、`elapsed`、环境快照（本 case `environment:"a"`）。

**依赖**：就绪检查；`api_client`；embeddings-capable tier `Embedding-v1` / `dep_local_bge_m3`；`constants.recent_window()`；`UsageRecord`/`UsagePage` 机器契约；机制 [`usage-metering` §4.5/§4.6](../../../20_system_design/mechanisms/usage-metering.md)；自动化入口 `at_dp_usage_02.py`。**不依赖**其它 Case；与 DP-EMB-01（基本 embedding）共享同一调用形态但各自独立执行。
