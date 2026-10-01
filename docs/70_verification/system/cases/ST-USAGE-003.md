<!-- STD_DOCUMENT_COVER_BEGIN -->
# ST-USAGE-003 — cursor 分页（limit=1）

> STD 使用入口：[项目采用说明与标准导航](../../../../README.md#std-entry)

| 文档字段 | 值 |
|---|---|
| Document ID | `ST-USAGE-003` |
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
| Canonical Path | `docs/70_verification/system/cases/ST-USAGE-003.md` |
| Supersedes | none |

> Reviewer、Approver、Approval Date 和 Release Tag 在进入相应状态时填写。Git commit/tag 是
> 外部不可变证据；不要在文档内容中伪造包含自身的 commit hash。
<!-- STD_DOCUMENT_COVER_END -->

### 模板定位：方案、用例与计划的边界

- **一 Case 一文档**：本 Case 文档 ID＝Case ID（`ST-USAGE-003`）；责任摘要、分类与优先级以 [系统测试方案 §3](../llmtier-system-test-scheme.md) 清单行为准。
- **来源**：系统设计 §8 Usage 查询接口（parent `llmtier-system-design`），设计验证项 `VRC-MGMT-006`；所属方案 `llmtier-system-test-scheme`。
- **边界**：系统层 Case（整软件系统组装，被测为 m5air 真实部署或按 tests.asset-design 约束的替身）；本文档持有实现状态，执行状态与 Verdict 只在 Run 报告。

### 状态语义：实现状态

| 状态 | 取值 | 唯一权威记录处 | 禁止 |
|---|---|---|---|
| 测试代码实现状态 | `Planned` / `Implemented` | 本文档 §7 | 计划中的测试函数冒充可执行入口 |
| 执行状态 | `NOT_RUN` / `BLOCKED` / `INVALID` | Run 报告 | 在本文档预填执行或判定 |
| 实际判定 Verdict | `PASS` / `FAIL` | 仅 Run 报告 | 在本文档预填 Actual 或 Verdict |

本 Case 沿 Case ID `ST-USAGE-003` 可追到方案清单行与 Run 报告。

## 1. Case 概述与责任

- Case ID / 来源 ID / 设计验证项 / 分类 / 优先级（引用方案清单）：`ST-USAGE-003` / 系统设计 §8 Usage 查询接口 / `VRC-MGMT-006` / boundary / P1（[方案清单 `ST-USAGE-003`](../llmtier-system-test-scheme.md)）；机制 `T-MET-PAGE`（[usage-metering 机制](../../../20_system_design/mechanisms/usage-metering.md) §4.5/§4.7 CON-METER-004）。
- **测试方法（§1.5 方法表行）**：边界值抽样 + 契约字段比对
- 要测什么（责任展开）：`GET /v1/usage?limit=1` 每页至多 1 条并给出 `next_cursor`；沿 cursor 取后续页，同 `snapshot_id`/`snapshot_at`、按 `(recorded_at,request_id)` 稳定推进、无重复无遗漏，`has_more=false` 时 `next_cursor=null`。`limit` `1..200` 默认 100，`cursor` 可选；首屏创建 `query_snapshots` 并冻结有序成员，返回 `next_cursor = "<snapshot_id>:<offset>"`；后续页按冻结视图读，`snapshot` 跨页不变。实现 `src/inference/usage.py::UsageRecorder._page`（`ORDER BY v.recorded_at,v.request_id`，`limit+1` 探测 `has_more`）。机制需求 `R-MET-02`；需求链 `LT-FUN-004`、`LT-INT-004/005/007`、`CT-USAGE-001`。
- 明确不测什么 / 失败含义：不测过期 cursor 拒绝（ST-USAGE-004）、主体隔离（ST-USAGE-006）、同 cursor 重放的逐字节幂等/冻结不变（ST-USAGE-007）、store 不可用（ST-USAGE-008）；不测时间窗元数据完整性（ST-USAGE-001）；不测 `limit` 取值范围校验（实现仅做整数转换）。失败含义＝分页游标契约破坏。

## 2. 被测入口与前置

- 被测入口声明与位置：Data Plane `GET /v1/usage`（`data`）与前置 `POST /v1/embeddings`。

```text
GET /v1/usage?from=<tight-from>&to=<tight-to>&limit=1
GET /v1/usage?from=<tight-from>&to=<tight-to>&limit=1&cursor=<sid>:1
Authorization: Bearer dev-data
```

- 初态构造（经公开入口）：**环境 A**（m5air 已部署实例，只读/无状态）。初始状态 = m5air 现有基线。**自含前置**：为得到 ≥2 条记录，先发 2 次 `POST /v1/embeddings`（`model="Embedding-v1"`，固定输入）并捕获各自 `X-Request-ID`；窗口使用**紧致动态窗口**（如 `from=now-5min`、`to=now+1min`，由 `now()` 生成，禁止硬编码日期），把分页范围限制在本次记录附近。embeddings deployment 见 `dep_local_bge_m3`。
- Fixture / 向量及版本：两次前置 embeddings（`rid_a`、`rid_b`）；紧致动态窗口；Run manifest 存档。
- 依赖的测试资产（tests.asset-design 文档）：`api_client`（data 主体 `principal_id=consumer`）；`conftest.py::pytest_configure` 就绪检查。

## 3. 输入构造

- 逐参数输入构造：两次前置 embeddings（同 ST-USAGE-002 形态），随后 `GET /v1/usage?from=<tight-from>&to=<tight-to>&limit=1`，再以首屏返回的 `next_cursor`：`GET /v1/usage?from=<tight-from>&to=<tight-to>&limit=1&cursor=<sid>:1`。
- 边界/非法取值及理由：`limit=1` 为边界；同一 `from`/`to` 必须在所有页保持**逐字节相同**，否则 `filter_digest` 不匹配会返回 400 `invalid_request`（`_page` 的 cursor 复核）；`cursor` 由首屏 `next_cursor` 原样带入。
- 规模 / 时间域：2 次写 + 分页查询直到 `has_more=false`（页数上限若干）；不发布时延 SLO。

## 4. 执行步骤与观察点

| Step | 动作 | 观察点 |
|---|---|---|
| 1 | `GET /healthz`/`GET /readyz`（`pytest_configure` 完成，不重复） | §2.1 基线 |
| 2 | 发 2 次 `POST /v1/embeddings`，各断言 200 | 捕获 `rid_a`、`rid_b` |
| 3 | `page1 = GET /v1/usage?from&to&limit=1` | 200；`len(data) == 1`；`has_more` 为 bool；`snapshot_id` 非空；若 `has_more=true` 则 `next_cursor` 匹配 `^<snapshot_id>:\d+$` 且非空，否则为 `null` |
| 4 | `c1 = page1.next_cursor`；`page2 = GET ?...&cursor=c1` | 200 且 `page2.snapshot_id == page1.snapshot_id`、`page2.snapshot_at == page1.snapshot_at` |
| 5 | 沿 `next_cursor` 继续（≤ 页上限）直到 `has_more=false` | `page1.data[0].request_id != page2.data[0].request_id`；累积所有 `request_id`，`rid_a`、`rid_b` 各恰出现 1 次 |
| 6 | 末页 | `has_more=false ⇒ next_cursor is null` |

- 重点关注步骤：① **cursor 形态与解析**——`<snapshot_id>:<offset>`；服务端按 `cursor.split(":",1)[0]` 取 snapshot、`[1]` 取 offset；把 `cursor` 当不透明字符串带回；② **跨页 snapshot 不变**——`snapshot_id`/`snapshot_at` 在 page1 与 page2 必须一致；若第二页出现**新** `snapshot_id` 即 FAIL；③ **稳定排序 `(recorded_at,request_id)`**；④ **`has_more`/`next_cursor` 同步**——`has_more=false ⇒ next_cursor=null`；⑤ **同 filter**——所有页 `from`/`to` 必须一致；⑥ **缺陷/注意（实现与 openapi 不符）**：handler 用 `_int_param` 只做 `int()` 转换，**不校验** openapi 的 `minimum:1`/`maximum:200`；即 `limit=0`/`limit=500` 不会被拒。本 case 不据此判 FAIL（只测合法 `limit=1`），但应在运行报告登记该"范围未校验"偏差。另：现有 [`ST-USAGE-003.py`](../../../../tests/system/cases/ST-USAGE-003.py) 只断言单页 `≤1` 与 `next_cursor` 非空，**未跟随 cursor 取第二页、未验证跨页同 snapshot/无重复无遗漏**；设计完整断言须补齐。

## 5. 独立 Oracle 与预期结果

- 独立 Oracle 来源与推导：机制 CON-METER-004/Step 4–5（首屏冻结 + 后续页读冻结视图 + 稳定排序）+ OpenAPI `UsagePage`。**判据语义以设计验证项 `VRC-MGMT-006` 为唯一权威**；本节仅细化不改写，冲突回溯设计修订。
- 互斥预期（成功 / 各错误分支）：page1：`200`，`data` 长 1，`has_more` bool；`has_more=true ⇒ next_cursor=="<snapshot_id>:1"`（非空），`false ⇒ null`；page2：`200`，`data` 长 ≤1，`snapshot_id`/`snapshot_at` 与 page1 相同，`request_id` 与 page1 不同；沿页累积：`rid_a`、`rid_b` 各出现恰 1 次；末页 `has_more=false` 且 `next_cursor=null`。

## 6. 错误路径、副作用与清理

- 错误出口与表现：`data` 超 `limit`、跨页 `snapshot_id` 变化、重复/遗漏本次 `request_id`、`has_more`/`next_cursor` 不变式破裂、排序不稳。
- 副作用断言与清理：**无需 teardown**——查询为只读，仅创建 10 分钟 TTL 的首屏 `query_snapshots`；两次 embeddings 属被测行为（不删用户 usage）。不创建/修改 provider/deployment/service-level、不写注入。退出前 `/readyz` 仍 7 tier；若误跑于 B 类则按计划销毁临时实例。

## 7. 自动化位置与状态

- 测试文件 / 测试函数：[`tests/system/cases/ST-USAGE-003.py`](../../../../tests/system/cases/ST-USAGE-003.py)（脚本须补齐跨页断言）。
- 单 Case 执行命令：`PYTHONPATH=src python3 -m pytest tests/system/cases/ST-USAGE-003.py -q`。
- 实现状态：Implemented；执行与 Verdict 归 Run 报告。

**判定口径（PASS/FAIL/BLOCKED/SKIP/NOT_RUN/INVALID）**：
- PASS：上述 page1/page2/累积/末页断言全部 match。
- FAIL：`data` 超 `limit`、跨页 `snapshot_id` 变化、重复/遗漏本次 `request_id`、`has_more`/`next_cursor` 不变式破裂、排序不稳。
- BLOCKED：断言逻辑/契约问题、embeddings 前置无法命中。
- SKIP：就绪检查不满足。
- INVALID：用 mock/替代路径冒充真实路径，或未命中真实分页而按行为判定。
- NOT_RUN：本 Case 有实现，本轮未执行时记 `NOT_RUN`。

**证据与 Run**：Run ID=`<date>/A-api`；保存两次前置 embeddings 的 `X-Request-ID`、所有分页请求（含 `cursor` 实际值）与响应（`data[].request_id`、`record_version`、`snapshot_id`、`snapshot_at`、`next_cursor`、`has_more`）、动态窗口值、发出命令、exit code、`elapsed`、环境快照（本 case `environment:"a"`）。

**依赖**：就绪检查；`api_client`；embeddings tier `Embedding-v1`/`dep_local_bge_m3`；机制 [`usage-metering` CON-METER-004](../../../20_system_design/mechanisms/usage-metering.md)；自动化入口 `ST-USAGE-003.py`。**不依赖**其它 Case；与 ST-USAGE-004（过期 cursor）、ST-USAGE-007（同 cursor 重放）共享 cursor 语义但各自独立执行。
